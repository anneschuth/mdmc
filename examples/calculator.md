# Simple Calculator

Read a simple arithmetic expression from stdin in the format: `number operator number`

For example: `12 + 34` or `100 - 57` or `6 * 7` or `144 / 12`

Supported operators: + - * /

Parse the two numbers and the operator, compute the result, and print it.
For division, print the integer result (truncate toward zero).
If dividing by zero, print "Error: division by zero" and exit with code 1.

Exit with code 0 on success.
