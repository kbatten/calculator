#!/usr/bin/env python

"""
recursive descent parser/tokenizer/evaluator bignum calculator

based off of Rob Pike's slides implementing one in golang
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
    # meta
    statement_list = 1000
    statement = 1001
    identifier = 1002
    expression = 1003

    operator = 1004
    number = 1005
    rational = 1006
    identifier = 1007

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
    def __str__(self):
        return str(self.val)

    def eval(self):
        return self.val

    # returns the most constrained type that matches the passed in value
    def value_as(self, value):
        return self

    # shrink the value to the smallest type possible
    def shrink(self):
        return self

    # get values v1 and v2 as the same underlying type (int, vector, matrix)
    @staticmethod
    def same(v1, v2):
        return (v1.value_as(v2), v2.value_as(v1))

    @staticmethod
    def binary_op(v1, op, v2):
        v1, v2 = Value.same(v1, v2)
        if op == '+':
            return v1.add(v2).shrink()


class Integer(Value):
    def __init__(self, str_val):
        self.val = int(str_val)

    def add(self, v):
        return Integer(self.val + v.val)


class Parser(object):
    def __init__(self):
        self.variables = {}
        self.cursor = 0
        self.data = ""



    def evaluate(self, data):
        # reset data and cursor, variable persist
        self.data = data
        self.cursor = 0

        # prime with first token
        return self.expression(self.next_tok_skip_whitespace())


    # Tokenizer functions

    # get the next token without advancing    
    def peek_tok(self):
        tok, _ = self._next_tok_and_cursor()
        return tok

    # get the next token and advance
    def next_tok(self):
        tok, self.cursor = self._next_tok_and_cursor()
        return tok

    # get the next non-whitespace token without advancing
    def peek_tok_skip_whitespace(self):
        cursor_saved = self.cursor
        tok, self.cursor = self._next_tok_and_cursor()
        while tok.typ == Token.whitespace:
            tok, self.cursor = self._next_tok_and_cursor()
        self.cursor = cursor_saved
        return tok

    # get the next non-whitespace token and advance
    def next_tok_skip_whitespace(self):
        tok, self.cursor = self._next_tok_and_cursor()
        while tok.typ == Token.whitespace:
            tok, self.cursor = self._next_tok_and_cursor()
        return tok

    def _next_tok_and_cursor(self):
        cursor = self.cursor
        if cursor >= len(self.data):
            return (Token(Token.eof, ''), cursor+1)

        c = self.data[cursor]
        if c == "\n":
            return (Token(Token.newline, '\n'), cursor+1)
        elif c == '(':
            return (Token(Token.left_paren, '('), cursor+1)
        elif c == ')':
            return (Token(Token.right_paren, ')'), cursor+1)
        elif c == '[':
            return (Token(Token.left_bracket, '['), cursor+1)
        elif c == ']':
            return (Token(Token.right_bracket, ']'), cursor+1)
        elif c == ';':
            return (Token(Token.semicolon, ';'), cursor+1)
        elif c == '+':
            return (Token(Token.operator, '+'), cursor+1)
        elif c == '=':
            return (Token(Token.assign, '='), cursor+1)

        elif c in " \t":
            # consume all but one space
            while c in " \t":
                cursor += 1
                if cursor >= len(self.data):
                    break
                c = self.data[cursor]
            return (Token(Token.whitespace, '<space>'), cursor)

        elif c.isdigit():
            text = ""
            while c.isdigit():
                text += c
                cursor += 1
                if cursor >= len(self.data):
                    break
                c = self.data[cursor]
            return (Token(Token.number, text), cursor)

        # identifier must start with alpha, but can then be alphanumeric
        elif c.isalpha():
            text = ""
            while c.isalnum():
                text += c
                cursor += 1
                if cursor >= len(self.data):
                    break
                c = self.data[cursor]
            return (Token(Token.identifier, text), cursor)

        raise Exception("unexpected " + c)


    # Grammar functions

    def expression(self, tok):
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
            return Value.binary_op(expr, tok.text, self.expression(self.next_tok_skip_whitespace()))  # recurse

        # assignment
        if tok_next.typ == Token.assign:
            identifier = tok.text
            tok = self.next_tok_skip_whitespace()
            val = self.expression(self.next_tok_skip_whitespace())  # recurse
            self.variables[identifier] = val
            return val

        raise Exception("after expresion: unexpected " + str(tok_next))


    def operand(self, tok):
        # an operator means a unary operation
        if tok.typ == Token.operator:
            expr = Value.unary_op(tok.text, self.expression(self.next_tok_skip_whitespace()))  # recurse

        elif tok.typ == Token.left_paren:
            expr = self.expression(self.next_tok_skip_whitespace())  # recurse
            tok = self.next_tok_skip_whitespace()
            if tok.typ != Token.right_paren:
                raise Exception("expected ')', found " + str(tok))

        elif tok.typ == Token.number or \
                tok.typ == Token.rational:
            expr = self.number(tok)

        elif tok.typ == Token.identifier:
            # first check if we are assigning, then evaluate
            tok_next = self.peek_tok_skip_whitespace()
            if tok_next.typ == Token.assign:
                self.next_tok_skip_whitespace()  # consume assignment operator
                self.variables[tok.text] = self.expression(self.next_tok_skip_whitespace())  # recurse
            expr = self.variables.get(tok.text, None)
            if expr is None:
                raise Exception(str(tok) + " undefined")

        else:
            raise Exception("unexpected " + str(tok))

        return expr


    def number(self, tok):
        return Integer(tok.text)


if __name__ == '__main__':
    p = Parser()
    while True:
        try:
            output = p.evaluate(input())
        except EOFError:
            break
        print(output)
        print()
        
