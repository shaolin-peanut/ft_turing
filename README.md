# ft_turing

Simulating a turing machine and writing 5 machine descriptions

### Machines

1. unary_add
2. palindrome
3. balanced_binary
4. is_even

---

# ft_turing

Un simulateur de Machine de Turing écrit en OCaml (programmation fonctionnelle).
Ce projet permet d'exécuter n'importe quelle machine décrite en JSON, y compris une **Machine de Turing Universelle (UTM)** capable de simuler d'autres machines.

## 📋 Pré-requis

- **OCaml** & **OPAM**
- **OCamlfind**
- **Yojson** (pour le parsing JSON)

Pour installer les dépendances :

```bash
opam install ocamlfind yojson
```

## 🛠️ Compilation

Le projet utilise un Makefile pour gérer la compilation du simulateur principal et de l'outil d'encodage.

# Compiler le simulateur (ft_turing) et l'encodeur

make re (ft_turing)
make encoder (encoder)

# Nettoyer les fichiers de build

make fclean

## 🚀 Usage Standard

Pour lancer une machine classique (palindrome, addition unaire simple, etc.) :

```
./ft_turing <fichier_json> <input>
```

## 🧠 La Machine Universelle (Machine 5)
Ce projet implémente la machine universelle $U_{9,3}$ décrite par Neary & Woods (2009). C'est une machine minimaliste (9 états, 3 symboles) qui simule un système de file d'attente (Bi-Tag System), qui lui-même simule une Machine de Turing.

# Fichiers concernés
- machines/utm_9_3_bootstrap.json : La machine universelle (le processeur).
- machines/unary_add_forward.json : La machine à simuler (le programme), optimisée pour ne faire que des déplacements vers la droite ("Forward-Only").srcs/encoder.ml : 
- L'outil qui compile la machine cible en une bande compatible avec $U_{9,3}$.

## ➡️ Procédure d'exécution
La simulation d'une machine par une autre demande beaucoup de ressources (plusieurs millions d'étapes pour une addition simple). Suivez ces étapes :

1. Compiler les outils
Assurez-vous que l'exécutable encoder est bien présent :

```
make encoder
```

2. Générer la bande (L'Encodage)
Nous convertissons la machine d'addition et son entrée (par exemple 11+1=) en format compatible $U_{9,3}$.

````
./encoder machines/unary_add_forward.json "11+1=" > machines/input_encoded.txt
````

3. Lancer la Simulation
Attention : L'affichage dans le terminal ralentit considérablement l'exécution. Il est fortement recommandé de rediriger la sortie vers un fichier pour voir le résultat final rapidement.

Méthode Rapide (Recommandée) :
```
./ft_turing machines/utm_9_3_bootstrap.json "$(cat machines/input_encoded.txt)" > resultat_final.txt
````

Méthode Visuelle (Pour le debug/fun) :
````
./ft_turing machines/utm_9_3_bootstrap.json "$(cat machines/input_encoded.txt)"
````

## ⚙️ Détails Techniques de l'UTM
- Forward-Only : La machine unary_add a été modifiée pour ne jamais revenir en arrière (LEFT), ce qui simplifie considérablement la simulation par un système de Tag (qui est une file d'attente).
- Bootstrap : La machine universelle démarre dans un état spécial BOOT pour trouver le début des données sur la bande (marqué par un X) avant de lancer le cycle de simulation standard à partir de l'état u1.
- Alphabet Adapté : L'alphabet original du papier ({c, b, $\delta$}) a été adapté en {c, b, d} pour respecter la contrainte de caractères uniques du sujet (longueur string = 1).
- Gestion du Vide : Le caractère blank du sujet est défini comme . pour permettre l'utilisation du caractère c (fond de bande) dans l'input.

