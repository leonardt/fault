* Initial conditions

.subckt my_init_cond_2 vc
* storage nodes
Ca vc_x 0 1p
* wiring
Rb vc_x vc 1
.ends

.subckt my_init_cond va vb vc
* storage nodes
Cc va 0 1p
Cd vb_x 0 1p
Xe vc_x my_init_cond_2
* wiring
Rf vb_x vb 1
Rg vc_x vc 1
.ends
