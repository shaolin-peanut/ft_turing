# ft_turing

Simulating a turing machine and writing 5 machine descriptions

### Machines

1. unary_add
2. palindrome
3. balanced_binary
4. is_even



## Run unary add long
transitions:

_ -> seperator
S -> scanright
E -> erasone
A -> addone
H -> Halt

R -> Right
L -> Left

X -> blank

\# -> Start of the input

S1_S1R_S+_A1R_E1_E.R_E._H.L_A1_A1R -> undary_addition machine encoded

example of input:

S1_S1R_S+_A1R_E1_E.R_E._H.L_A1_A1R#1+1=


## Run unary add

1 -> scanright 1    | A -> to state scanright, write 1, RIGTH
2 -> scanright +    | B -> to state addone, write 1, RIGTH
3 -> erasone 1      | C -> to state erasone, write ., RIGTH
4 -> erasone .      | D -> to state HALT, write ., RIGTH
5 -> addone 1       | E -> to state addone, write 1, RIGTH
6 -> addone =       | F -> to state erasone, write 1, LEFT


unary addition encoded:

1A2B3C4D5E6F