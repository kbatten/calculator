#!/usr/bin/env python

"""
recursive descent parser/tokenizer/evaluator APLish calculator

it is similar to a normal calculator but precedence is by order, not by
operation type

based off of Rob Pike's implimentation in golang
https://www.youtube.com/watch?v=PXoG0WX0r_E
"""


# python 2/3 compatibility
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals
)
import sys
if sys.version_info < (3, 0):
    input = raw_input


# APL GRAMMAR
#
# operand
#   ( expression )
#   ( expression ) [ expression ]...
#   operand
#   number
#   rational
#   vector
#   variable
#   operand [ expression ]...
#   unary_op expression
#
# expression
#   operand
#   operand binary_op expr
#
# statement_list
#   statement
#   statement ';' statement
#
# statement
#   identifier '=' expression
#   expression


class Token(object):
    """ Token constants """
    # meta
    statement_list = 1000
    statement = 1001
    identifier = 1002
    expression = 1003

    operator = 1004
    number = 1005
    rational = 1006
    identifier = 1007
    vector = 1008

    # character
    eof = 2000
    newline = 2001
    left_paren = 2002
    right_paren = 2003
    left_bracket = 2004
    right_bracket = 2005
    semicolon = 2006
    assign = 2007
    whitespace = 2008

    def __init__(self, typ, text):
        self.typ = typ
        self.text = text

    def __str__(self):
        return self.text

    def __repr__(self):
        return "(" + str(self.typ) + ", " + self.text + ")"


class Value(object):
    """ Base value object, subclass types from this """
    def __init__(self, str_val):
        self.str_val = str_val
        self.val = str_val

    def __str__(self):
        return str(self.val)

    def value_as(self, value):
        """
        get this Value as the most constrained type that matches the passed
        in value. either returns self or promotes to a higher order Value
        """
        return self

    def shrink(self):
        """
        get this Value as the most constrained type that it can be. for
        example a one element vector will shrink to an Integer
        """
        return self

    @staticmethod
    def same(val1, val2):
        """
        get values v1 and v2 as the same underlying type (int, vector, matrix)
        """
        return (val1.value_as(val2), val2.value_as(val1))

    @staticmethod
    def unary_op(value, op):
        """ perform a unary operation on the value """
        if op == '-':
            return value.neg().shrink()

    @staticmethod
    def binary_op(val1, op, val2):
        """ perform a binary operation on the two values """
        val1, val2 = Value.same(val1, val2)
        if op == '+':
            return val1.add(val2).shrink()
        elif op == '-':
            return val1.sub(val2).shrink()
        elif op == '*':
            return val1.multiply(val2).shrink()
        elif op == '**':
            return val1.power(val2).shrink()


class Integer(Value):
    """ Integer type """
    def __init__(self, str_val):
        super(Integer, self).__init__(str_val)
        self.val = int(str_val)

    def neg(self):
        """ negate Integer """
        return Integer("-" + self.str_val)

    def add(self, value):
        """ add two Integers """
        return Integer(self.val + value.val)

    def sub(self, value):
        """ subtract two Integers """
        return Integer(self.val - value.val)

    def multiply(self, value):
        """ multiple to Integers """
        return Integer(self.val * value.val)

    def power(self, value):
        """ raise self to value exponent """
        return Integer(self.val ** value.val)

    def value_as(self, value):
        """ get this value as either an Integer or Vector """
        if value.__class__.__name__ == "Vector":
            return Vector(str(self.val))
        return self


class Vector(Value):
    """ Vector type """
    def __init__(self, str_val):
        super(Vector, self).__init__(str_val)
        self.val = [Integer(val) for val in str_val.split(' ')]

    def __str__(self):
        return ' '.join([ele.str_val for ele in self.val])

    @staticmethod
    def _element_unary_op(value, op):
        """ perform element by element unary operation """
        return Vector(' '.join([str(Value.unary_op(v, op)) for v in value.val]))

    @staticmethod
    def _element_binary_op(value1, op, value2):
        """
        perform element by element binary operation

        single element vector is operated on all elements
        two multi element vectors operate on the element pairs by index
        """
        # [a] op [b, c] = [a op b, a op c]
        if len(value1.val) == 1:
            return Vector(' '.join([str(Value.binary_op(value1.val[0], op, v)) for v in value2.val]))
        # [a, b] op [c] = [a op c, b op c]
        elif len(value2.val) == 1:
            return Vector(' '.join([str(Value.binary_op(v, op, value2.val[0])) for v in value1.val]))
        # [a, b] op [c, d] = [a op c, b op d]
        elif len(value1.val) == len(value2.val):
            return Vector(' '.join([str(Value.binary_op(v1, op, v2)) for v1, v2 in zip(value1.val, value2.val)]))
        # [a, b] op [c, d, e] is invalid
        raise Exception("mismatched vector lengths")

    def neg(self):
        """ negate all values in this Vector """
        return Vector._element_unary_op(self, '-')

    def add(self, value):
        """ add two Vectors """
        return Vector._element_binary_op(self, '+', value)

    def sub(self, value):
        """ subtract two Vectors """
        return Vector._element_binary_op(self, '-', value)

    def multiply(self, value):
        """ elementwise multiplication """
        return Vector._element_binary_op(self, '*', value)

    def power(self, value):
        """ elementwise exponentiation """
        return Vector._element_binary_op(self, '**', value)

    def shrink(self):
        """ for a one element list, return the single element """
        if len(self.val) == 1:
            return self.val[0]
        return self


class Parser(object):
    """ parse and tokenize an input string """
    def __init__(self):
        self.variables = {}
        self.cursor = 0
        self.data = ""

    def evaluate(self, data):
        """ evaluate the input expression """
        # reset data and cursor, variables persist
        self.data = data
        self.cursor = 0

        # prime with first token
        # save result to 'ans'
        ans = self.expression(self.next_tok_skip_whitespace())
        self.variables['ans'] = ans
        return ans

    # Tokenizer functions

    def peek_tok(self):
        """ get the next token without advancing """
        tok, _ = self._next_tok_and_cursor()
        return tok

    def next_tok(self):
        """ get the next token and advance """
        tok, self.cursor = self._next_tok_and_cursor()
        return tok

    def peek_tok_skip_whitespace(self):
        """ get the next non-whitespace token without advancing """
        cursor_saved = self.cursor
        tok, self.cursor = self._next_tok_and_cursor()
        while tok.typ == Token.whitespace:
            tok, self.cursor = self._next_tok_and_cursor()
        self.cursor = cursor_saved
        return tok

    def next_tok_skip_whitespace(self):
        """ get the next non-whitespace token and advance """
        tok, self.cursor = self._next_tok_and_cursor()
        while tok.typ == Token.whitespace:
            tok, self.cursor = self._next_tok_and_cursor()
        return tok

    def _next_tok_and_cursor(self):
        """ scan the data for the next token """
        cursor = self.cursor
        if cursor >= len(self.data):
            return (Token(Token.eof, ''), cursor+1)

        char = self.data[cursor]
        if char == "\n":
            return (Token(Token.newline, '\n'), cursor+1)
        elif char == '(':
            return (Token(Token.left_paren, '('), cursor+1)
        elif char == ')':
            return (Token(Token.right_paren, ')'), cursor+1)
        elif char == '[':
            return (Token(Token.left_bracket, '['), cursor+1)
        elif char == ']':
            return (Token(Token.right_bracket, ']'), cursor+1)
        elif char == ';':
            return (Token(Token.semicolon, ';'), cursor+1)
        elif char == '+':
            return (Token(Token.operator, '+'), cursor+1)
        elif char == '-':
            return (Token(Token.operator, '-'), cursor+1)
        elif char == '*':
            # either multiplication or exponentiation
            if cursor+1 >= len(self.data) or \
                    self.data[cursor+1] != "*":
                return (Token(Token.operator, '*'), cursor+1)
            if self.data[cursor+1] == "*":
                return (Token(Token.operator, '**'), cursor+2)
        elif char == '=':
            return (Token(Token.assign, '='), cursor+1)

        elif char in " \t":
            # consume all but one space
            while char in " \t":
                cursor += 1
                if cursor >= len(self.data):
                    break
                char = self.data[cursor]
            return (Token(Token.whitespace, '<space>'), cursor)

        # number (vector is handled as tokens)
        elif char.isdigit():
            text = ""
            while char.isdigit():
                text += char
                cursor += 1
                if cursor >= len(self.data):
                    break
                char = self.data[cursor]
            return (Token(Token.number, text), cursor)

        # identifier must start with alpha, but can then be alphanumeric
        elif char.isalpha():
            text = ""
            while char.isalnum():
                text += char
                cursor += 1
                if cursor >= len(self.data):
                    break
                char = self.data[cursor]
            return (Token(Token.identifier, text), cursor)

        raise Exception("unexpected " + char)

    # Grammar functions

    def expression(self, tok):
        """ evaluate an expression token """

        # left side
        expr = self.operand(tok)

        # right side
        tok_next = self.peek_tok_skip_whitespace()

        if tok_next.typ == Token.newline or \
                tok_next.typ == Token.eof or \
                tok_next.typ == Token.right_paren or \
                tok_next.typ == Token.right_bracket or \
                tok_next.typ == Token.semicolon:
            return expr

        # an operator on the right means binary operation
        if tok_next.typ == Token.operator:
            tok = self.next_tok_skip_whitespace()
            return Value.binary_op(expr, tok.text, self.expression(self.next_tok_skip_whitespace()))

        # assignment
        if tok_next.typ == Token.assign:
            identifier = tok.text
            tok = self.next_tok_skip_whitespace()
            val = self.expression(self.next_tok_skip_whitespace())
            self.variables[identifier] = val
            return val

        raise Exception("after expresion: unexpected " + str(tok_next))

    def operand(self, tok):
        """ evalate an operand token """

        # an operator means a unary operation
        if tok.typ == Token.operator:
            expr = Value.unary_op(self.expression(self.next_tok_skip_whitespace()), tok.text)

        elif tok.typ == Token.left_paren:
            expr = self.expression(self.next_tok_skip_whitespace())
            tok = self.next_tok_skip_whitespace()
            if tok.typ != Token.right_paren:
                raise Exception("expected ')', found " + str(tok))

        # either a single number or a list seperated by whitespace
        elif tok.typ == Token.number or \
                tok.typ == Token.rational:
            is_vector = False
            tok_next = self.peek_tok_skip_whitespace()
            tok_list = [tok]
            # read in numbers till we hit something else
            while tok_next.typ == Token.number or \
                    tok.typ == Token.rational:
                is_vector = True
                tok_list = tok_list + [tok_next]
                self.next_tok_skip_whitespace()
                tok_next = self.peek_tok_skip_whitespace()
            if is_vector is False:
                expr = self.number(tok)
            else:
                expr = self.vector(tok_list)

        elif tok.typ == Token.identifier:
            # first check if we are assigning, then evaluate
            tok_next = self.peek_tok_skip_whitespace()
            if tok_next.typ == Token.assign:
                self.next_tok_skip_whitespace()  # consume assignment operator
                self.variables[tok.text] = self.expression(self.next_tok_skip_whitespace())
            expr = self.variables.get(tok.text, None)
            if expr is None:
                raise Exception(str(tok) + " undefined")

        else:
            raise Exception("unexpected " + str(tok))

        return expr

    def number(self, tok):
        """ evaluate a number token """
        return Integer(tok.text)

    def vector(self, tok_list):
        """ evaluate a vector token """
        return Vector(' '.join([tok.text for tok in tok_list]))


if __name__ == '__main__':
    parser = Parser()
    while True:
        try:
            result = parser.evaluate(input())
        except EOFError:
            break
        print(result)
        print()
