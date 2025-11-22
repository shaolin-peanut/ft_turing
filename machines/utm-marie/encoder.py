import json
import sys

def get_unary(n):
    """Génère une suite de 'b' pour l'encodage unaire."""
    return "b" * n

def get_c_block(n):
    """Génère une suite de 'c' pour les règles."""
    return "c" * n

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 encoder.py <machine.json> <input_string>")
        sys.exit(1)

    # 1. CHARGEMENT DE LA MACHINE
    with open(sys.argv[1], 'r') as f:
        tm = json.load(f)
    
    input_str = sys.argv[2]

    # 2. CONFIGURATION DE L'ENCODAGE
    # On mappe chaque symbole et état à un index (1, 2, 3...)
    alphabet = tm['alphabet']
    states = tm['states']
    
    # Dictionnaires pour retrouver l'index rapidement
    sym_map = {char: i+1 for i, char in enumerate(alphabet)}
    state_map = {name: i+1 for i, name in enumerate(states)}
    
    q = len(alphabet) # Nombre total de symboles (paramètre 'q' du papier)
    
    # 3. CONSTANTES U9,3 (Table 1 du papier)
    # S = c^2, G = delta, V = delta c c, H = becbc
    S = "cc"
    G = "delta"
    V = "delta c c " # Avec espaces pour lisibilité
    H = "becbc "
    
    # 4. GÉNÉRATION DES RÈGLES (Partie Gauche de la bande)
    # Structure : H + [Transitions P(e,a)] + V^2 + [Identité P(a)] + V^3
    
    rules_stream = H

    # A. Les Transitions (P(e_j, a_i))
    # On doit itérer à l'envers (du plus grand index au plus petit) car la machine scanne vers la gauche.
    # Ordre papier : e_{h-1}a_q ... e_1 a_1
    
    # On exclut l'état HALT des règles de transition (généralement le dernier)
    # On suppose que le dernier état dans la liste est le HALT
    active_states = states[:-1] 
    
    for state_name in reversed(active_states):
        state_idx = state_map[state_name]
        
        for sym in reversed(alphabet):
            sym_idx = sym_map[sym]
            
            # Chercher la transition correspondante dans le JSON
            trans = None
            if state_name in tm['transitions']:
                for t in tm['transitions'][state_name]:
                    if t['read'] == sym:
                        trans = t
                        break
            
            # Si transition trouvée, on encode la règle
            if trans:
                next_state_idx = state_map[trans['to_state']]
                write_sym_idx = sym_map[trans['write']]
                
                # FORMULE (Table 2 pour U9,3, transition standard)
                # Encode: delta c c delta delta c^(8*m*q + 2) delta c^(8*k)
                # où m = next_state_idx, k = write_sym_idx
                rule_str = (
                    "delta c c delta delta " + 
                    get_c_block(8 * next_state_idx * q + 2) + 
                    " delta " + 
                    get_c_block(8 * write_sym_idx)
                )
                rules_stream += rule_str + " " + V
            else:
                # Si pas de transition (crash/halt implicite), on met une règle bidon ou vide
                # Pour simplifier, on suppose que la machine est bien formée.
                pass

    # B. Séparateur V^2
    rules_stream += V 

    # C. Les Règles d'Identité (P(a_i)) - Pour que les symboles restent eux-mêmes
    # Ordre papier : a_q ... a_1
    for sym in reversed(alphabet):
        sym_idx = sym_map[sym]
        # FORMULE (Table 2 pour U9,3, colonne P(ai))
        # Encode: delta delta c c delta c^(8*i)
        rule_str = "delta delta c c delta " + get_c_block(8 * sym_idx)
        rules_stream += rule_str + " " + V
        
    # D. Séparateur V^3 (Fin des règles)
    rules_stream += V + V
    
    # 5. GÉNÉRATION DES DONNÉES (Partie Droite de la bande)
    # Structure : S + G + [Etat Initial] + [Bande Input]
    
    data_stream = S + " " + G + " "
    
    # Encoder l'état initial
    # Formule Table 1: <e_j> = b^(4jq)
    init_state_idx = state_map[tm['initial']]
    data_stream += get_unary(4 * init_state_idx * q) + " "
    
    # Encoder la bande d'entrée (symbole par symbole)
    # Le format BTS intercale des delta : <e> <a1> delta <a2> delta ...
    # Mais ici on démarre, donc on a juste : <etat> <sym1> delta <sym2> delta ...
    
    for i, char in enumerate(input_str):
        if char not in sym_map:
            print(f"Erreur: Caractère '{char}' inconnu dans l'alphabet.")
            sys.exit(1)
            
        sym_idx = sym_map[char]
        # Formule Table 1: <a_i> = b^(4i-1)
        data_stream += get_unary(4 * sym_idx - 1)
        
        # Ajouter un delta après chaque symbole sauf potentiellement le dernier ?
        # Dans l'exemple 3.1, on voit "b... delta b... delta".
        data_stream += " delta "

    # Finir par des blancs (c c c)
    data_stream += "c c c"

    # 6. ASSEMBLAGE FINAL
    # On nettoie les espaces en trop
    full_tape = (rules_stream + data_stream).replace("  ", " ").strip()
    
    print(full_tape)

if __name__ == "__main__":
    main()