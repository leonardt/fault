def pwc_to_pwl(pwc, t_stop, t_tr, init=0):
    # add initial value if necessary
    if len(pwc) == 0 or pwc[0][0] != 0:
        pwc = pwc.copy()
        pwc.insert(0, (0, init))

    # then create piecewise-linear implementation
    # of the piecewise-constant stimulus
    retval = [pwc[0]]
    for k in range(1, len(pwc)):
        t_prev, v_prev = pwc[k - 1]
        t_curr, v_curr = pwc[k]

        retval += [(t_curr, v_prev)]
        retval += [(t_curr + t_tr, v_curr)]

    # add final value
    retval += [(t_stop, pwc[-1][1])]

    # return new waveform
    return retval
