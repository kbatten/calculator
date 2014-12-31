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


import random


# APL GRAMMAR
#
# operand
#   ( expression )
#   ( expression ) [ expression ]...
#   operand
#   number  -- Integer
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
        if self.typ == Token.eof:
            return "<eof>"
        elif self.typ == Token.newline:
            return "<nl>"
        elif self.typ == Token.whitespace:
            return "<ws>"
        return self.text

    def __repr__(self):
        return "(" + str(self.typ) + ", " + str(self) + ")"


class Value(object):
    """ Base value object, subclass types from this """
    def __init__(self, val):
        self.val = val

    def __str__(self):
        return str(self.val)

    def __repr__(self):
        return "(" + self.__class__.__name__ + ", " + str(self) + ")"

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
    def same(value1, value2):
        """
        get values v1 and v2 as the same underlying type (int, vector, matrix)
        """
        return (value1.value_as(value2), value2.value_as(value1))

    @staticmethod
    def unary_op(value, op):
        """ perform a unary operation on the value """
        if op == '-':
            return value.neg().shrink()
        elif op == '?':
            return value.roll().shrink()

    @staticmethod
    def binary_op(value1, op, value2):
        """ perform a binary operation on the two values """
        value1, value2 = Value.same(value1, value2)
        if op == '+':
            return value1.add(value2).shrink()
        elif op == '-':
            return value1.sub(value2).shrink()
        elif op == '*':
            return value1.multiply(value2).shrink()
        elif op == '**':
            return value1.power(value2).shrink()
        elif op == '+.*':
            return value1.dot_product(value2).shrink()


class Integer(Value):
    """ Integer type """

    def value_as(self, value):
        """ get this value as either an Integer or Vector """
        if value.__class__.__name__ == "Vector":
            return Vector([self])
        return self

    # operations

    def neg(self):
        """ negate Integer """
        return Integer(-self.val)

    def roll(self):
        """ generate a random integer from 1 to val """
        if self.val < 1:
            raise Exception("invalid roll value " + self.val)
        return Integer(random.randint(1, self.val))

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


class Vector(Value):
    """ Vector type """

    def __str__(self):
        return ' '.join([str(ele) for ele in self.val])

    @staticmethod
    def _element_unary_op(value, op):
        """ perform element by element unary operation """
        return Vector([Value.unary_op(v, op) for v in value.val])

    @staticmethod
    def _element_binary_op(value1, op, value2):
        """
        perform element by element binary operation

        single element vector is operated on all elements
        two multi element vectors operate on the element pairs by index
        """
        # [a] op [b, c] = [a op b, a op c]
        if len(value1.val) == 1:
            return Vector([Value.binary_op(value1.val[0], op, v) for v in value2.val])
        # [a, b] op [c] = [a op c, b op c]
        elif len(value2.val) == 1:
            return Vector([Value.binary_op(v, op, value2.val[0]) for v in value1.val])
        # [a, b] op [c, d] = [a op c, b op d]
        elif len(value1.val) == len(value2.val):
            return Vector([Value.binary_op(v1, op, v2) for v1, v2 in zip(value1.val, value2.val)])
        # [a, b] op [c, d, e] is invalid
        raise Exception("mismatched vector lengths")

    def shrink(self):
        """ for a one element list, return the single element """
        if len(self.val) == 1:
            return self.val[0].shrink()
        return self

    # operations

    def neg(self):
        """ negate all values in this Vector """
        return Vector._element_unary_op(self, '-')

    def roll(self):
        return Vector._element_unary_op(self, '?')

    def sum(self):
        """ sum all the values in the vector """
        acc = self.val[0]
        for value in self.val[1:]:
            acc = Value.binary_op(acc, '+', value)
        return acc

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

    def dot_product(self, value):
        """ dot product (inner product) of two vectors """
        if len(self.val) == len(value.val):
            # element multiple
            vec = Vector._element_binary_op(self, '*', value)
            # summation
            return vec.sum()

        raise Exception("mismatched vector lengths")


class Parser(object):
    """ tokenize, parse and evaluate an input string """
    def __init__(self):
        self.variables = {}
        self.tokens = []

        self.data = ""
        self.cursor = 0

    def execute(self, data):
        """ evaluate the input expression """
        # single line execution only

        # reset data and tokens, don't reset variables
        self.data = data
        self.cursor = 0
        self.tokens = []

        self._tokenize()

        # evaluate the tokens directly, prime with first token
        ans = self._expression(self._next_tok_skip_whitespace())

        # save result to ans variable
        self.variables['ans'] = ans
        return ans

    # Scanner functions

    def _tokenize(self):
        """ scan input data and output a list of tokens """
        tok = self._scan_tok()
        while tok.typ != Token.eof:
            self.tokens.append(tok)
            tok = self._scan_tok()
        self.tokens.append(tok)  # eof

    def _scan_tok(self):
        """ scan in the next token and advance the cursor """
        if self.cursor >= len(self.data):
            return Token(Token.eof, '')

        tok = None
        tok_len = 1

        char = self.data[self.cursor]
        if char == "\n":
            tok = Token(Token.newline, "\n")
        elif char == '(':
            tok = Token(Token.left_paren, '(')
        elif char == ')':
            tok = Token(Token.right_paren, ')')
        elif char == '[':
            tok = Token(Token.left_bracket, '[')
        elif char == ']':
            tok = Token(Token.right_bracket, ']')
        elif char == ';':
            tok = Token(Token.semicolon, ';')

        # either addition or dot product
        elif char == '+':
            if self.cursor+2 < len(self.data) and \
                    self.data[self.cursor:self.cursor+3] == "+.*":
                tok = Token(Token.operator, '+.*')
                tok_len = 3
            else:
                tok = Token(Token.operator, '+')

        elif char == '-':
            tok = Token(Token.operator, '-')
        elif char == '?':
            tok = Token(Token.operator, '?')

        # either multiplication or exponentiation
        elif char == '*':
            if self.cursor+1 >= len(self.data) or \
                    self.data[self.cursor+1] != "*":
                tok = Token(Token.operator, '*')
            elif self.data[self.cursor+1] == "*":
                tok = Token(Token.operator, '**')
                tok_len = 2
        elif char == '=':
            tok = Token(Token.assign, '=')

        elif char in " \t":
            # consume all but one space
            tok_len = 0
            while char in " \t":
                tok_len += 1
                if self.cursor + tok_len >= len(self.data):
                    break
                char = self.data[self.cursor + tok_len]
            tok = Token(Token.whitespace, ' ')

        # number (vector is handled as tokens)
        elif char.isdigit():
            text = ""
            tok_len = 0
            while char.isdigit():
                text += char
                tok_len += 1
                if self.cursor + tok_len >= len(self.data):
                    break
                char = self.data[self.cursor + tok_len]
            tok = Token(Token.number, text)

        # identifier must start with alpha, but can then be alphanumeric
        elif char.isalpha():
            text = ""
            tok_len = 0
            while char.isalnum():
                text += char
                tok_len += 1
                if self.cursor + tok_len >= len(self.data):
                    break
                char = self.data[self.cursor + tok_len]
            tok = Token(Token.identifier, text)

        else:
            raise Exception("unexpected " + char)

        self.cursor += tok_len

        return tok

    # Grammar functions

    def _expression(self, tok):
        """ evaluate an expression token """

        # left side
        expr = self._operand(tok)

        # right side
        tok_next = self._peek_tok_skip_whitespace()

        if tok_next.typ == Token.newline or \
                tok_next.typ == Token.eof or \
                tok_next.typ == Token.right_paren or \
                tok_next.typ == Token.right_bracket or \
                tok_next.typ == Token.semicolon:
            return expr

        # an operator on the right means binary operation
        if tok_next.typ == Token.operator:
            tok = self._next_tok_skip_whitespace()
            return Value.binary_op(expr, tok.text, self._expression(self._next_tok_skip_whitespace()))

        # assignment
        if tok_next.typ == Token.assign:
            identifier = tok.text
            tok = self._next_tok_skip_whitespace()
            val = self._expression(self._next_tok_skip_whitespace())
            self.variables[identifier] = val
            return val

        raise Exception("after expresion: unexpected " + str(tok_next))

    def _operand(self, tok):
        """ evalate an operand token """

        # an operator means a unary operation
        if tok.typ == Token.operator:
            expr = Value.unary_op(self._expression(self._next_tok_skip_whitespace()), tok.text)

        elif tok.typ == Token.left_paren:
            expr = self._expression(self._next_tok_skip_whitespace())
            tok = self._next_tok_skip_whitespace()
            if tok.typ != Token.right_paren:
                raise Exception("expected ')', found " + str(tok))

        # either a single number or a list seperated by whitespace
        elif tok.typ == Token.number:
            is_vector = False
            tok_next = self._peek_tok_skip_whitespace()
            value_list = [Parser.number(tok)]
            # read in numbers till we hit something else
            while tok_next.typ == Token.number:
                is_vector = True
                value_list.append(Parser.number(tok_next))
                self._next_tok_skip_whitespace()
                tok_next = self._peek_tok_skip_whitespace()
            if is_vector is False:
                expr = value_list[0]
            else:
                expr = self.vector(value_list)

        elif tok.typ == Token.identifier:
            # first check if we are assigning, then evaluate
            tok_next = self._peek_tok_skip_whitespace()
            if tok_next.typ == Token.assign:
                self._next_tok_skip_whitespace()  # consume assignment operator
                self.variables[tok.text] = self._expression(self._next_tok_skip_whitespace())
            expr = self.variables.get(tok.text, None)
            if expr is None:
                raise Exception(str(tok) + " undefined")

        else:
            raise Exception("unexpected " + str(tok))

        return expr

    def _peek_tok_skip_whitespace(self):
        """ get the next non-whitespace token but don't modify tokenlist """
        for tok in self.tokens:
            if tok.typ != Token.whitespace:
                return tok

    def _next_tok_skip_whitespace(self):
        """ get the next non-whitespace token and modify tokenlist """
        while True:
            tok = self.tokens.pop(0)
            if tok.typ != Token.whitespace:
                return tok

    # Value functions

    @staticmethod
    def number(tok):
        """ evaluate a number token """
        return Integer(int(tok.text))

    @staticmethod
    def vector(value_list):
        """ evaluate a vector token """
        return Vector(value_list)


def main():
    """ entry point """
    parser = Parser()
    ans = ""
    while True:
        try:
            if ans is not None:
                print(">>> ", end='')
            else:
                print("... ", end='')
            ans = parser.execute(input())
        except EOFError:
            print()
            break
        print("\t" + str(ans), end='\n\n')

if __name__ == '__main__':
    main()
