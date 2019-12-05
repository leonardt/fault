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

        if retval[-1][0] >= t_curr:
            assert retval[-2][0] <= t_curr, \
                    'non-increasing pwc steps at time' % t_curr
            if retval[-2][0] == t_curr:
                # two values at the same time, just drop the earlier
                #print('dropping old thing')
                retval.pop()
                old_t, old_v = retval.pop()
                v_prev = old_v
                #print('prev is now', retval[-2:])
            else:
                # make the previous thing happen faster than t_tr
                #print('DOING THE HALFWAY THING')
                halfway_time = (retval[-2][0] + t_curr)/2
                retval[-1] = (halfway_time, retval[-1][1])

        #print('times', t_curr, t_curr + t_tr)
        retval += [(t_curr, v_prev)]
        retval += [(t_curr + t_tr, v_curr)]

    # add final value
    # cut off anything after t_stop
    while len(retval) > 0 and retval[-1][0] >= t_stop:
        #print('removing one from end')
        retval.pop()
    retval += [(t_stop, pwc[-1][1])]

    # return new waveform
    return retval
