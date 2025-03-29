- rule 110 based turing machine
    - rule 110 is a cellular automaton proven to be turing complete using tag systems
    - if we can make a turing machine that can update cellular automata, we can make a universal turing machine that takes in an encoded turing machine description, discards non-relevant parts, and simulates the rest by going through cellular automata generations
    - The open question is, how do I encode the transition table in a format that the CA will "understand"? I need to separate thing with clear delimiters, patterns, but all in binary!
- encoding stuff
    - encoding a turing machines, so it can be easily read by another turing machine
        - fixed size ordering
        - unary addition state transitions
    |state|symbol|goto |write|dir|
    |-----|------|-----|-----|---|
    |q0   |1     |q0   |1    |R  |
    |q0   |+     |q2   |1    |R  |
    |q1   |1     |q1   |.    |R  |
    |q1   |.     |qh   |.    |L  |
    |q2   |1     |q2   |1    |R  |
    |q2   |=     |q1   |.    |L  |
        - or as a bare string `q0 1 q0 1 R q0 + q2 1 R q1 1 q1 . R q1 . qh . L q2 1 q2 1 R q2 = q1 . L`
    - the UTM is a turing whose input is a machine description on the rigth side, and the machine's input on the left side, separated by a #
    - to encode the current state, we replace the current symbol with the state name plus the symbol when writing a change to the tape
    - different encodings for state transitions keys
        - "scanright" 1 -> "A"
        - "scanright" + -> "B"
        - "eraseone" 1 -> "C"
        - "eraseone" . -> "D"
        - "addone" 1 -> "E"
        - "addone" = -> "F"
        - halt -> "H"
    - so the updated encoding, with encoded transitions keys, is
    |key|next_key|dir|
    |A  |A       |R  |
    |B  |E       |R  |
    |C  |D       |R  |
    |D  |H       |L  |
    |E  |E       |R  |
    |F  |D       |L  |