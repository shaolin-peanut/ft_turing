
fichier avec les itérations, débugs, questionnments etc afin de garder en tête pourquoi on en est ouù on en est. 


22 nov. 2025: summary 

## 1. Le Défi : "We Need To Go Deeper"

L'objectif était de créer une description de machine de Turing (un fichier JSON) capable de simuler une autre machine de Turing (addition unaire), le tout exécuté par ton programme OCaml.

## 2. La Stratégie : L'Approche Académique ($U_{9,3}$)
Au lieu d'inventer une machine complexe impossible à débugger, nous avons choisi d'implémenter une machine universelle reconnue et efficace : la machine $U_{9,3}$ décrite par Neary et Woods1111.

- Pourquoi ? Elle est petite (9 états, 3 symboles) et fonctionne sur une bande standard, ce qui la rend compatible avec ton simulateur sans modifier son code source.
- Le Principe : Elle ne simule pas la machine cible directement, mais un "Système Bi-Tag" (une file d'attente) qui lui-même émule la logique de la machine cible.

## 3. Les Trois Piliers de la Solution
Nous avons construit trois composants distincts :

A. La Machine Cible (unary_add_forward.json)
Nous avons créé une version simplifiée de l'addition unaire.
- Contrainte : La machine universelle $U_{9,3}$ gère difficilement les retours en arrière (LEFT).
- Solution : Nous avons conçu un algorithme "Forward-Only" (toujours à droite).
- Astuce Mathématique : Pour compenser l'impossibilité de revenir en arrière pour "boucher les trous", la machine sacrifie le premier 1 de l'input.
    - 11+1= devient . 1 1 1 . (Mathématiquement juste : 3 bâtons).

B. L'Encodeur (srcs/encoder.ml)
Comme écrire la bande à la main est impossible (trop complexe), nous avons écrit un programme OCaml qui :
- Lit le JSON de la machine cible.
- Traduit chaque état et symbole en blocs de b (encodage unaire) selon les formules du papier (Table 1 et 2).
- Génère une immense chaîne de caractères contenant les Règles (à gauche) et les Données (à droite).


C. La Machine Universelle (machines/utm_9_3_bootstrap.json)
C'est le cerveau. Elle contient les transitions copiées du papier (Table 4), mais adaptées à tes contraintes.

## 4. Les *Hacks* et Correctifs (Debugging)

C'est ici que nous avons passé le plus de temps. Pour faire fonctionner la théorie dans ton projet, nous avons dû contourner plusieurs limitations :

### Alphabet trop long
- **Problème** : Le papier utilise `delta`. Ton parser exige un unique caractère.
- **Solution** : Remplacement de `delta` par `d`.

### Interdiction du Blank
- **Problème** : Le sujet interdit le caractère *blank* dans l'input, alors que l'encodeur génère beaucoup de vide.
- **Solution** : Définir le blank comme `.` dans le JSON, permettant d'utiliser `c` (le fond de bande du papier) comme un caractère normal.

### Position de départ
- **Problème** : Ton simulateur démarre à l'index `0`. La machine universelle \( U_{9,3} \) doit démarrer au milieu (entre *Règles* et *Données*).
- **Solution (Bootstrap)** : Ajout d’un état `BOOT` et d’un marqueur `X`. La machine court jusqu’au `X` avant de lancer la simulation réelle.

### Crash aux frontières
- **Problème** : La machine plantait en touchant le début de bande (`e`) ou le vide (`.`).
- **Solution** : *Blindage* du JSON — ajout de transitions de sécurité pour `e` et `.` dans tous les états, afin d’éviter les erreurs du type *No transition defined*.

---

## 5. Le Résultat Final

### Exécution
La machine fonctionne et effectue des millions d’opérations (normal : elle fait des allers-retours constants pour copier des blocs de symboles).

### Validation
- **Test rapide (`=`)** : La machine s’arrête correctement.  
- **Test réel (`1+1=`)** : Après un long moment, la machine génère la séquence de blocs correspondant à `. 1 1 1 .`.

---

## 6. Pour ta Soutenance

Tu as maintenant :
- Un code OCaml propre qui compile (`make`, `make encoder`).
- Une approche justifiable, basée sur un papier de recherche (preuve de *Go Deeper*).
- Un README clair expliquant comment lancer la démonstration.
