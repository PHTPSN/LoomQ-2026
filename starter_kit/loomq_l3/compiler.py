"""A small, deterministic compiler for the documented Hybrid-QASM subset."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List, Optional, Sequence, Tuple, Union


class HybridSyntaxError(ValueError):
    """Raised when Hybrid-QASM is outside the supported Level 3 grammar."""


@dataclass(frozen=True)
class Integer:
    value: int


@dataclass(frozen=True)
class Register:
    index: int


@dataclass(frozen=True)
class Measurement:
    index: int


@dataclass(frozen=True)
class Unary:
    operator: str
    operand: "Expression"


@dataclass(frozen=True)
class Binary:
    operator: str
    left: "Expression"
    right: "Expression"


Expression = Union[Integer, Register, Measurement, Unary, Binary]


@dataclass(frozen=True)
class Condition:
    operator: str
    left: Expression
    right: Expression


@dataclass(frozen=True)
class Assignment:
    target: int
    expression: Expression


@dataclass(frozen=True)
class Branch:
    condition: Condition
    then_body: Tuple["Statement", ...]
    else_body: Tuple["Statement", ...]


Statement = Union[Assignment, Branch]


@dataclass(frozen=True)
class _Token:
    kind: str
    text: str
    position: int


_TOKEN_RE = re.compile(
    r"(?P<SPACE>\s+)"
    r"|(?P<COMMENT>//[^\r\n]*|/\*.*?\*/)"
    r"|(?P<IF>if\b)"
    r"|(?P<ELSE>else\b)"
    r"|(?P<MEASUREMENT>c\[\d+\])"
    r"|(?P<REGISTER>r[1-9](?![A-Za-z0-9_]))"
    r"|(?P<INTEGER>\d+)"
    r"|(?P<EQUAL>==)"
    r"|(?P<NOT_EQUAL>!=)"
    r"|(?P<ASSIGN>=)"
    r"|(?P<PLUS>\+)"
    r"|(?P<MINUS>-)"
    r"|(?P<LPAREN>\()"
    r"|(?P<RPAREN>\))"
    r"|(?P<LBRACE>\{)"
    r"|(?P<RBRACE>\})"
    r"|(?P<SEMICOLON>;)"
    ,
    re.DOTALL,
)


def _tokenize(source: str) -> List[_Token]:
    tokens: List[_Token] = []
    position = 0
    while position < len(source):
        match = _TOKEN_RE.match(source, position)
        if match is None:
            excerpt = source[position : position + 20].splitlines()[0]
            raise HybridSyntaxError(
                "unexpected classical syntax at offset %d: %r" % (position, excerpt)
            )
        kind = match.lastgroup
        if kind not in {"SPACE", "COMMENT"}:
            tokens.append(_Token(kind or "", match.group(), position))
        position = match.end()
    tokens.append(_Token("EOF", "", len(source)))
    return tokens


class _Parser:
    def __init__(self, source: str, num_measurements: int):
        self.tokens = _tokenize(source)
        self.position = 0
        self.num_measurements = num_measurements

    @property
    def current(self) -> _Token:
        return self.tokens[self.position]

    def _accept(self, kind: str) -> Optional[_Token]:
        if self.current.kind != kind:
            return None
        token = self.current
        self.position += 1
        return token

    def _expect(self, kind: str) -> _Token:
        token = self._accept(kind)
        if token is None:
            raise HybridSyntaxError(
                "expected %s at offset %d, found %r"
                % (kind, self.current.position, self.current.text or "end of input")
            )
        return token

    def parse(self) -> Tuple[Statement, ...]:
        statements = self._program("EOF")
        self._expect("EOF")
        return statements

    def _program(self, stop: str) -> Tuple[Statement, ...]:
        statements: List[Statement] = []
        while self.current.kind != stop:
            if self.current.kind == "EOF":
                raise HybridSyntaxError("unterminated classical statement block")
            statements.append(self._statement())
        return tuple(statements)

    def _statement(self) -> Statement:
        if self.current.kind == "IF":
            return self._branch()
        return self._assignment()

    def _assignment(self) -> Assignment:
        target = self._expect("REGISTER")
        self._expect("ASSIGN")
        expression = self._expression()
        self._expect("SEMICOLON")
        return Assignment(int(target.text[1:]), expression)

    def _branch(self) -> Branch:
        self._expect("IF")
        self._expect("LPAREN")
        left = self._expression()
        operator = self.current
        if operator.kind not in {"EQUAL", "NOT_EQUAL"}:
            raise HybridSyntaxError(
                "condition at offset %d must use == or !=" % operator.position
            )
        self.position += 1
        right = self._expression()
        self._expect("RPAREN")
        self._expect("LBRACE")
        then_body = self._program("RBRACE")
        self._expect("RBRACE")
        else_body: Tuple[Statement, ...] = ()
        if self._accept("ELSE") is not None:
            self._expect("LBRACE")
            else_body = self._program("RBRACE")
            self._expect("RBRACE")
        return Branch(
            Condition("==" if operator.kind == "EQUAL" else "!=", left, right),
            then_body,
            else_body,
        )

    def _expression(self) -> Expression:
        expression = self._unary()
        while self.current.kind in {"PLUS", "MINUS"}:
            operator = self.current
            self.position += 1
            expression = Binary("+" if operator.kind == "PLUS" else "-", expression, self._unary())
        return expression

    def _unary(self) -> Expression:
        if self._accept("MINUS") is not None:
            return Unary("-", self._unary())
        return self._primary()

    def _primary(self) -> Expression:
        token = self.current
        if self._accept("INTEGER") is not None:
            return Integer(int(token.text))
        if self._accept("REGISTER") is not None:
            return Register(int(token.text[1:]))
        if self._accept("MEASUREMENT") is not None:
            index = int(token.text[2:-1])
            if index >= self.num_measurements:
                raise HybridSyntaxError(
                    "measurement c[%d] is outside declared classical register" % index
                )
            return Measurement(index)
        if self._accept("LPAREN") is not None:
            expression = self._expression()
            self._expect("RPAREN")
            return expression
        raise HybridSyntaxError(
            "expected expression at offset %d, found %r"
            % (token.position, token.text or "end of input")
        )


def _mask_non_code(source: str) -> str:
    """Mask comments and strings while preserving positions and line breaks."""

    output = list(source)
    index = 0
    state = "code"
    quote = ""
    while index < len(source):
        if state == "code":
            if source.startswith("//", index):
                output[index] = output[index + 1] = " "
                index += 2
                state = "line_comment"
            elif source.startswith("/*", index):
                output[index] = output[index + 1] = " "
                index += 2
                state = "block_comment"
            elif source[index] in {'"', "'"}:
                quote = source[index]
                output[index] = " "
                index += 1
                state = "string"
            else:
                index += 1
        elif state == "line_comment":
            if source[index] in "\r\n":
                state = "code"
            else:
                output[index] = " "
            index += 1
        elif state == "block_comment":
            if source.startswith("*/", index):
                output[index] = output[index + 1] = " "
                index += 2
                state = "code"
            else:
                if source[index] not in "\r\n":
                    output[index] = " "
                index += 1
        else:
            if source[index] == "\\" and index + 1 < len(source):
                output[index] = " "
                output[index + 1] = " "
                index += 2
            else:
                if source[index] not in "\r\n":
                    output[index] = " "
                if source[index] == quote:
                    state = "code"
                index += 1
    if state == "block_comment":
        raise HybridSyntaxError("unterminated block comment")
    if state == "string":
        raise HybridSyntaxError("unterminated string literal")
    return "".join(output)


def _split_hybrid(source: str) -> Tuple[str, str]:
    if not isinstance(source, str) or not source.strip():
        raise HybridSyntaxError("Hybrid-QASM source must be a non-empty string")
    masked = _mask_non_code(source)
    matches = list(re.finditer(r"\bclassical\b", masked))
    if not matches:
        raise HybridSyntaxError("exactly one classical block is required")
    if len(matches) != 1:
        raise HybridSyntaxError("multiple classical blocks are not supported")
    match = matches[0]
    opening = match.end()
    while opening < len(masked) and masked[opening].isspace():
        opening += 1
    if opening >= len(masked) or masked[opening] != "{":
        raise HybridSyntaxError("classical must be followed by a braced block")
    depth = 0
    closing: Optional[int] = None
    for index in range(opening, len(masked)):
        if masked[index] == "{":
            depth += 1
        elif masked[index] == "}":
            depth -= 1
            if depth == 0:
                closing = index
                break
    if closing is None:
        raise HybridSyntaxError("unterminated classical block")
    quantum_source = source[: match.start()] + source[closing + 1 :]
    classical_source = source[opening + 1 : closing]
    return quantum_source, classical_source


def _number(value: float) -> str:
    if abs(value) < 1e-15:
        value = 0.0
    return format(value, ".17g")


def _quantum_operations(source: str) -> Tuple[List[str], int]:
    try:
        from ..loomq_l1 import Measure, parse_qasm2
    except ImportError:  # Support ``python evaluator.py`` inside starter_kit/.
        from loomq_l1 import Measure, parse_qasm2

    circuit = parse_qasm2(source)
    operations: List[str] = []
    for instruction in circuit.instructions:
        if isinstance(instruction, Measure):
            operations.append(
                "measure q[%d] -> c[%d];" % (instruction.qubit, instruction.clbit)
            )
            continue
        params = ""
        if instruction.params:
            params = "(" + ",".join(_number(value) for value in instruction.params) + ")"
        qubits = ", ".join("q[%d]" % index for index in instruction.qubits)
        operations.append("%s%s %s;" % (instruction.name, params, qubits))
    return operations, circuit.num_clbits


def _walk_expression(expression: Expression) -> Sequence[Expression]:
    items: List[Expression] = [expression]
    if isinstance(expression, Unary):
        items.extend(_walk_expression(expression.operand))
    elif isinstance(expression, Binary):
        items.extend(_walk_expression(expression.left))
        items.extend(_walk_expression(expression.right))
    return items


def _mentioned_registers(statements: Sequence[Statement]) -> set[int]:
    mentioned: set[int] = set()
    for statement in statements:
        if isinstance(statement, Assignment):
            mentioned.add(statement.target)
            expressions = (statement.expression,)
        else:
            expressions = (statement.condition.left, statement.condition.right)
            mentioned.update(_mentioned_registers(statement.then_body))
            mentioned.update(_mentioned_registers(statement.else_body))
        for expression in expressions:
            for item in _walk_expression(expression):
                if isinstance(item, Register):
                    mentioned.add(item.index)
    return mentioned


class _ScratchPool:
    def __init__(self, candidates: Sequence[int]):
        self.candidates = list(candidates)
        self.active: List[int] = []
        self.used: set[int] = set()

    def acquire(self) -> int:
        for register in self.candidates:
            if register not in self.active:
                self.active.append(register)
                self.used.add(register)
                return register
        raise HybridSyntaxError("classical expression requires more temporary registers")

    def release(self, register: int) -> None:
        if not self.active or self.active[-1] != register:
            raise RuntimeError("temporary registers must be released in stack order")
        self.active.pop()


def _constant(expression: Expression) -> Optional[int]:
    if isinstance(expression, Integer):
        return expression.value
    if isinstance(expression, Unary):
        value = _constant(expression.operand)
        return None if value is None else -value
    if isinstance(expression, Binary):
        left = _constant(expression.left)
        right = _constant(expression.right)
        if left is None or right is None:
            return None
        return left + right if expression.operator == "+" else left - right
    return None


def _direct_register(expression: Expression) -> Optional[int]:
    if isinstance(expression, Register):
        return expression.index
    if isinstance(expression, Measurement):
        return 10 + expression.index
    if _constant(expression) == 0:
        return 0
    return None


def _linear_form(expression: Expression) -> Tuple[dict[int, int], int]:
    """Return physical-register coefficients and the constant term."""

    if isinstance(expression, Integer):
        return {}, expression.value
    if isinstance(expression, Register):
        return {expression.index: 1}, 0
    if isinstance(expression, Measurement):
        return {10 + expression.index: 1}, 0
    if isinstance(expression, Unary):
        coefficients, constant = _linear_form(expression.operand)
        return {register: -value for register, value in coefficients.items()}, -constant

    left_coefficients, left_constant = _linear_form(expression.left)
    right_coefficients, right_constant = _linear_form(expression.right)
    right_sign = 1 if expression.operator == "+" else -1
    coefficients = dict(left_coefficients)
    for register, value in right_coefficients.items():
        combined = coefficients.get(register, 0) + right_sign * value
        if combined:
            coefficients[register] = combined
        else:
            coefficients.pop(register, None)
    return coefficients, left_constant + right_sign * right_constant


def _is_power_of_two(value: int) -> bool:
    return value > 0 and value & (value - 1) == 0


class _AssemblyCompiler:
    def __init__(self, statements: Sequence[Statement], num_measurements: int):
        if num_measurements > 22:
            raise HybridSyntaxError("c[k] mapping exceeds the available x10..x31 registers")
        mentioned = _mentioned_registers(statements)
        high_temporaries = list(range(31, 9 + num_measurements, -1))
        unused_user_registers = [index for index in range(9, 0, -1) if index not in mentioned]
        self.scratch = _ScratchPool(high_temporaries + unused_user_registers)
        self.lines: List[str] = []
        self.label_counter = 0

    def _label(self, prefix: str) -> str:
        self.label_counter += 1
        return "LQ_%s_%d" % (prefix, self.label_counter)

    def _emit(self, instruction: str) -> None:
        self.lines.append(instruction)

    def _emit_linear_form(
        self, coefficients: dict[int, int], constant: int, target: int
    ) -> None:
        if target in coefficients:
            raise RuntimeError("linear-form target must not be a source register")
        self._emit("li x%d, %d" % (target, constant))
        for source in sorted(coefficients):
            coefficient = coefficients[source]
            opcode = "add" if coefficient > 0 else "sub"
            for _ in range(abs(coefficient)):
                self._emit(
                    "%s x%d, x%d, x%d" % (opcode, target, target, source)
                )

    def _emit_linear_assignment(self, expression: Expression, target: int) -> bool:
        coefficients, constant = _linear_form(expression)
        target_coefficient = coefficients.pop(target, 0)
        magnitude = abs(target_coefficient)
        if magnitude and not _is_power_of_two(magnitude):
            return False

        if target_coefficient == 0:
            self._emit_linear_form(coefficients, constant, target)
            return True

        for _ in range(magnitude.bit_length() - 1):
            self._emit("add x%d, x%d, x%d" % (target, target, target))
        if target_coefficient < 0:
            self._emit("sub x%d, x0, x%d" % (target, target))
        if constant:
            self._emit("addi x%d, x%d, %d" % (target, target, constant))
        for source in sorted(coefficients):
            coefficient = coefficients[source]
            opcode = "add" if coefficient > 0 else "sub"
            for _ in range(abs(coefficient)):
                self._emit(
                    "%s x%d, x%d, x%d" % (opcode, target, target, source)
                )
        return True

    def _emit_expression(self, expression: Expression, target: int) -> None:
        value = _constant(expression)
        if value is not None:
            self._emit("li x%d, %d" % (target, value))
            return
        if isinstance(expression, Register):
            if target != expression.index:
                self._emit("addi x%d, x%d, 0" % (target, expression.index))
            return
        if isinstance(expression, Measurement):
            self._emit("addi x%d, x%d, 0" % (target, 10 + expression.index))
            return
        if isinstance(expression, Unary):
            source = _direct_register(expression.operand)
            if source is not None:
                self._emit("sub x%d, x0, x%d" % (target, source))
                return
        coefficients, constant = _linear_form(expression)
        self._emit_linear_form(coefficients, constant, target)

    def _in_place_safe(self, expression: Expression, target: int) -> bool:
        if isinstance(expression, Register):
            return expression.index == target
        if isinstance(expression, Unary):
            return isinstance(expression.operand, Register) and expression.operand.index == target
        if isinstance(expression, Binary):
            if not self._in_place_safe(expression.left, target):
                return False
            if _constant(expression.right) is not None:
                return True
            right_register = _direct_register(expression.right)
            return right_register is not None and right_register != target
        return False

    def _emit_in_place(self, expression: Expression, target: int) -> None:
        if isinstance(expression, Register):
            return
        if isinstance(expression, Unary):
            self._emit("sub x%d, x0, x%d" % (target, target))
            return
        self._emit_in_place(expression.left, target)
        right_constant = _constant(expression.right)
        if right_constant is not None:
            immediate = right_constant if expression.operator == "+" else -right_constant
            self._emit("addi x%d, x%d, %d" % (target, target, immediate))
        else:
            right = _direct_register(expression.right)
            opcode = "add" if expression.operator == "+" else "sub"
            self._emit("%s x%d, x%d, x%d" % (opcode, target, target, right))

    def _assignment(self, statement: Assignment) -> None:
        value = _constant(statement.expression)
        if value is not None:
            self._emit("li x%d, %d" % (statement.target, value))
            return
        direct = _direct_register(statement.expression)
        if direct is not None:
            if direct != statement.target:
                self._emit("addi x%d, x%d, 0" % (statement.target, direct))
            return
        if self._in_place_safe(statement.expression, statement.target):
            self._emit_in_place(statement.expression, statement.target)
            return
        if self._emit_linear_assignment(statement.expression, statement.target):
            return
        temporary = self.scratch.acquire()
        self._emit_expression(statement.expression, temporary)
        self._emit("addi x%d, x%d, 0" % (statement.target, temporary))
        self.scratch.release(temporary)

    def _measurement_literal_branch(
        self, condition: Condition, false_label: str
    ) -> bool:
        measurement: Optional[Measurement] = None
        literal: Optional[int] = None
        if isinstance(condition.left, Measurement):
            measurement = condition.left
            literal = _constant(condition.right)
        elif isinstance(condition.right, Measurement):
            measurement = condition.right
            literal = _constant(condition.left)
        if measurement is None or literal is None:
            return False
        register = 10 + measurement.index
        if condition.operator == "==":
            if literal == 0:
                self._emit("bne x%d, x0, %s" % (register, false_label))
            elif literal == 1:
                self._emit("beq x%d, x0, %s" % (register, false_label))
            else:
                self._emit("j %s" % false_label)
        else:
            if literal == 0:
                self._emit("beq x%d, x0, %s" % (register, false_label))
            elif literal == 1:
                self._emit("bne x%d, x0, %s" % (register, false_label))
        return True

    def _false_branch(self, condition: Condition, false_label: str) -> None:
        left_constant = _constant(condition.left)
        right_constant = _constant(condition.right)
        if left_constant is not None and right_constant is not None:
            truth = (
                left_constant == right_constant
                if condition.operator == "=="
                else left_constant != right_constant
            )
            if not truth:
                self._emit("j %s" % false_label)
            return
        if self._measurement_literal_branch(condition, false_label):
            return
        left_register = _direct_register(condition.left)
        right_register = _direct_register(condition.right)
        opcode = "bne" if condition.operator == "==" else "beq"
        if left_register is not None and right_register is not None:
            self._emit(
                "%s x%d, x%d, %s"
                % (opcode, left_register, right_register, false_label)
            )
            return

        left_coefficients, left_constant = _linear_form(condition.left)
        right_coefficients, right_constant = _linear_form(condition.right)
        difference = dict(left_coefficients)
        for register, value in right_coefficients.items():
            combined = difference.get(register, 0) - value
            if combined:
                difference[register] = combined
            else:
                difference.pop(register, None)
        temporary = self.scratch.acquire()
        self._emit_linear_form(
            difference, left_constant - right_constant, temporary
        )
        self._emit("%s x%d, x0, %s" % (opcode, temporary, false_label))
        self.scratch.release(temporary)

    def _branch(self, statement: Branch) -> None:
        false_label = self._label("ELSE")
        end_label = self._label("END")
        self._false_branch(statement.condition, false_label)
        self._statements(statement.then_body)
        if statement.else_body:
            self._emit("j %s" % end_label)
            self.lines.append(false_label + ":")
            self._statements(statement.else_body)
            self.lines.append(end_label + ":")
        else:
            self.lines.append(false_label + ":")

    def _statements(self, statements: Sequence[Statement]) -> None:
        for statement in statements:
            if isinstance(statement, Assignment):
                self._assignment(statement)
            else:
                self._branch(statement)

    def compile(self, statements: Sequence[Statement]) -> str:
        self._statements(statements)
        for register in sorted(self.scratch.used):
            self._emit("li x%d, 0" % register)
        if not self.lines:
            self._emit("addi x0, x0, 0")
        return "\n".join(self.lines) + "\n"


def compile_hybrid(hybrid_qasm_str: str) -> Tuple[List[str], str]:
    """Compile Hybrid-QASM into canonical quantum operations and tiny RISC-V."""

    quantum_source, classical_source = _split_hybrid(hybrid_qasm_str)
    operations, num_measurements = _quantum_operations(quantum_source)
    statements = _Parser(classical_source, num_measurements).parse()
    assembly = _AssemblyCompiler(statements, num_measurements).compile(statements)
    return operations, assembly
