* Circuit to test current inputs and outputs
* in_c: input current
* in_v: input voltage
* out_c: output current = in_v / 100 Ohm
* out_v: output voltage = in_c * 500 Ohm

.subckt mycurrenttest in_c in_v out_c out_v

R1 in_v 0 100
* TODO mirror current
R4 out_c 0 123

R2 in_c 0 500
R3 in_c out_v 10

.ends
