from collections import defaultdict
from fault.actions import Poke

def mlingua_target(cls):
    class MLinguaTarget(cls):

        @staticmethod
        def is_mlingua(action):
            return (hasattr(action, 'port')
                    and getattr(action.port, 'representation', None) == 'mlingua')
        
        def run(self, *args, **kwargs):
            assert (len(args) > 0 and isinstance(args[0], list),
                    'Expected first arg to "target.run" to be an action list')
            actions = args[0]

            # check if there are any mLingua actions and set up mLingua acordingly
            has_ml_poke = any(self.is_mlingua(a) for a in actions)
            if has_ml_poke:
                #self.add_decl('PWLMethod', 'pm') 
                #self.add_assign('pm', 'new')
                self.add_decl('PWLMethod', 'pm=new')
                self.add_decl('`get_timeunit', '')
                self.includes.append('mLingua_pwl.vh')
                
                # sort out pokes by port
                pokes = defaultdict(list)
                time = 0
                for a in actions:
                    if self.is_mlingua(a):
                        p = a.port
                        pokes[p].append((time, a))
                    # TODO am I missing other ways the time can advance? certainly flow control will be a problem
                    # Cast to float here is only to make it throw an exception earlier
                    delay_attr = getattr(a, 'delay', 0)
                    delay = 0 if delay_attr is None else float(delay_attr)
                    time += delay

                # update pokes in-place depending on the next poke to the same port
                for poke_list in pokes.values():
                    # look at the value of the current and next point, replace value with 'pm.write(p0, slope, time)'
                    for i, (t, poke) in enumerate(poke_list):
                        next_val = poke_list[i+1][1].value if i != len(poke_list)-1 else poke.value
                        next_time = poke_list[i+1][0] if i != len(poke_list)-1 else 1
                        assert next_time != t, f'Cannot have 2 PWL pokes at the same time, check {poke.port}'
                        slope = (next_val - poke.value) / (next_time - t)
                        poke.value = f'pm.write({poke.value}, {slope}, `get_time)'

            super().run(*args, **kwargs)

        # Originally I was going to do everything in make_poke, but I can't because I need to know where the 
        # value is going next
        #def make_poke(self, i, action):
        #    if is_mlingua(action):
        #        # edit the action's value to be mLingua friendly
        #        style = getattr(action, 'style', 'pwc')
        #        pwl = (style == 'pwl' or style == 'pwc_or_pwl')
        #        
        #        
        #    super().make_poke(i, action)
    return MLinguaTarget
