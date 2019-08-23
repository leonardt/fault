* Initial conditions

.subckt my_init_cond_3 vc
* storage nodes
Ca vc_x 0 1p
* wiring
Rb vc_x vc 1
.ends

.subckt my_init_cond_2 vb vc
* storage nodes
Cc vb_x 0 1p
Xd vc_x my_init_cond_3
* wiring
Re vb_x vb 1
Rf vc_x vc 1
.ends

.subckt my_init_cond va vb vc
* storage nodes
Cg va_x 0 1p
Xh vb_x vc_x my_init_cond_2
* wiring
Ri va_x va 1
Rj vb_x vb 1
Rk vc_x vc 1
.ends
