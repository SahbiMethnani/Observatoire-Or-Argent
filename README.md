# Observatoire Or & Argent

Application web Streamlit d'analyse quantitative des prix de l'or (XAU/USD) et de l'argent (XAG/USD) sur dix ans, avec une étude approfondie de l'année en cours, une interpolation de Newton, le calcul des dérivées et la détection des points d'inflexion.

## 1. Le métier du site

### Le marché des métaux précieux

L'or et l'argent sont les deux principaux métaux précieux échangés dans le monde. Ils jouent plusieurs rôles à la fois :

- **Valeur refuge** : en période d'incertitude (crise financière, tensions géopolitiques, inflation), les investisseurs se tournent vers l'or, dont la valeur ne dépend pas d'un émetteur.
- **Réserve des banques centrales** : l'or fait partie des réserves officielles de nombreux États.
- **Usage industriel** : l'argent est un métal industriel majeur (électronique, panneaux solaires, batteries), ce qui le rend plus sensible au cycle économique que l'or.
- **Actif de diversification** : leur corrélation modérée avec les actions et les devises en fait un outil de gestion du risque.

Les prix sont cotés en **dollars américains par once troy** (environ 31,1 grammes). Le site utilise les contrats à terme continus (`GC=F` pour l'or, `SI=F` pour l'argent), proches du prix au comptant.

### Ce que fait le site

Le site joue le rôle d'un poste d'analyse pour un étudiant, un analyste ou un investisseur qui veut comprendre le comportement de ces deux métaux :

| Besoin | Réponse du site |
| --- | --- |
| Où en est-on par rapport au passé ? | Historique de 10 ans, performance comparée en base 100, bilan annuel |
| Quelle est la situation cette année ? | Analyse détaillée des 12 derniers mois : tendance, volatilité, risque, momentum |
| Les deux métaux évoluent-ils ensemble ? | Matrices de covariance et de corrélation, ACP, ratio Or/Argent |
| Peut-on modéliser la courbe ? | Interpolation polynomiale de Newton sur la dernière année |
| La tendance accélère-t-elle ou ralentit-elle ? | Dérivées première et seconde, points d'inflexion, extrema |

## 2. Concepts utilisés

### Indicateurs de marché

- **Rendement logarithmique** : variation relative quotidienne du prix, `r = ln(S_t / S_(t-1))`. Additif dans le temps.
- **Volatilité annualisée** : écart-type des rendements multiplié par la racine de 252 (nombre de séances par an). Mesure l'amplitude des variations.
- **TCAM** : taux de croissance annuel moyen composé sur la période.
- **Drawdown** : baisse depuis le dernier plus haut. Le drawdown maximal mesure la pire perte subie par un détenteur.
- **Moyennes mobiles (20, 50, 200 jours)** : lissent le prix pour identifier la tendance. Le croisement des moyennes est un signal classique.
- **Bandes de Bollinger** : enveloppe de plus ou moins deux écarts-types autour de la moyenne à 20 jours. Un prix hors de la bande signale un mouvement extrême.
- **RSI (14 jours)** : indicateur de momentum entre 0 et 100. Au-dessus de 70, le marché est considéré en surachat; en dessous de 30, en survente.
- **VaR 95 %** : perte journalière qui n'est dépassée que 5 % du temps.
- **Ratio Or/Argent** : nombre d'onces d'argent nécessaires pour acheter une once d'or. Les opérateurs l'utilisent pour juger la valorisation relative des deux métaux.

### Statistiques matricielles

- **Matrice de covariance** : mesure la co-variation des rendements de l'or et de l'argent, annualisée.
- **Matrice de corrélation** : version normalisée entre -1 et 1. Une corrélation élevée indique que les deux métaux réagissent aux mêmes forces.
- **ACP (analyse en composantes principales)** : diagonalise la covariance. La première composante représente le facteur commun "métaux précieux"; la seconde, ce qui distingue l'or de l'argent.
- **Déterminant, trace, conditionnement** : résumés de la matrice. Un conditionnement élevé signale une quasi-colinéarité.

### Analyse numérique

- **Interpolation de Newton** : construit le polynôme passant exactement par un ensemble de points (nœuds) pris sur la courbe des 12 derniers mois, à l'aide des différences divisées :

  `P(t) = c0 + c1 (t - x0) + c2 (t - x0)(t - x1) + ...`

  Les nœuds de Tchebychev évitent le phénomène de Runge (oscillations aux extrémités avec des nœuds équidistants).
- **Dérivée première f'** : pente de la courbe. Positive, le prix monte; négative, il baisse.
- **Dérivée seconde f''** : courbure. Positive (convexe), le mouvement s'accélère vers le haut; négative (concave), il s'accélère vers le bas.
- **Point d'inflexion** : instant où f'' change de signe, c'est-à-dire où la courbure s'inverse. C'est souvent un signal précoce de changement de dynamique.
- **Extremum** : instant où f' change de signe (maximum ou minimum local).
- **Savitzky-Golay** : filtre qui dérive des données bruitées sans amplifier le bruit.
- **Newton-Raphson** : méthode itérative `x_(n+1) = x_n - f(x_n) / f'(x_n)` utilisée ici pour affiner les zéros de P' et P''.

### État de la tendance

| f' | f'' | Lecture |
| --- | --- | --- |
| > 0 | > 0 | Hausse qui s'accélère |
| > 0 | < 0 | Hausse qui ralentit |
| < 0 | > 0 | Baisse qui ralentit |
| < 0 | < 0 | Baisse qui s'accélère |


## 3. Sources de données

- **Yahoo Finance** via la bibliothèque open source `yfinance` (source principale).
- **Stooq** via ses fichiers CSV ouverts (repli automatique).
- Import manuel d'un CSV (colonnes `Date`, `Or`, `Argent`) si les deux API sont inaccessibles.



## 7. Limites

- Un polynôme d'interpolation de degré élevé est instable hors de la zone des nœuds : il sert à décrire la courbe passée, pas à prévoir.
- Le nombre de points d'inflexion détectés dépend de la fenêtre de lissage.