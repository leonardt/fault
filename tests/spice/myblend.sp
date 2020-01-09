* Circuit that produces a weighted average of "a" and "b"
* Output is (1.2*b + 3.4*a)/(1.2 + 3.4)

.subckt myblend a b c

R0 a c 1.2e3
R1 b c 3.4e3

.ends
