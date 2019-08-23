* NMOS/PMOS models from
* https://people.rit.edu/lffeee/SPICE_Examples.pdf

.model EENMOS NMOS (VTO=0.4 KP=432E-6 GAMMA=0.2 PHI=.88)
.model EEPMOS PMOS (VTO=-0.4 KP=122E-6 GAMMA=0.2 PHI=.88)

.subckt sram_snm lbl lblb vdd vss wl

* inverter with lblb output
MP0 lblb_x lbl_x vdd vdd EEPMOS w=0.7u l=0.1u
MN0 lblb_x lbl_x vss vss EENMOS w=0.4u l=0.1u

* inverter with lbl output
MP1 lbl_x lblb_x vdd vdd EEPMOS w=0.7u l=0.1u
MN1 lbl_x lblb_x vss vss EENMOS w=0.4u l=0.1u

* access switches
MN2 lbl wl lbl_x vss EENMOS w=1.2u l=0.1u
MN3 lblb wl lblb_x vss EENMOS w=1.2u l=0.1u

.ends
