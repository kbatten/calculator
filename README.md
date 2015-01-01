APLish calculator
-----------------
based off of Rob Pike's ivy implimentation in golang

https://www.youtube.com/watch?v=PXoG0WX0r_E

Implements
----------
* integers
* vectors
* variables
* addition
* multiplication
* exponentiation
* subtraction
* random number generation
* vector generator with iota (range 1-X)
* vector generator with rho (repeated values)
* dot (inner) product

Examples
--------
```
>>> 1 + 2
        3
 
>>> 2 4 5 * 2
        4 8 10
 
>>> ans ** 3
        64 512 1000
 
>>> 2 3 4 +.* 7 4 2
        34

>>> 12-65
        -53

>>> x = ans
        -53

>>> 32+x
        -21

>>> ? 54
        34

>>> ? 87 23 4 1 889234
        26 6 1 1 123046

>>> iota 4
        1 2 3 4

>>> 3 rho 9
        9 9 9

>>> 5 rho 2 3 4
        2 3 4 2 3
```

Problems
--------
negation is wonky
