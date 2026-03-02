# ═══════════════════════════════════════════════════════════════
# Beautiful Graph Demonstrations
# A collection of visually stunning graph patterns
# ═══════════════════════════════════════════════════════════════

# ───────────────────────────────────────────────────────────────
# 1. THE PENTAGRAM (Five-Pointed Star)
# ───────────────────────────────────────────────────────────────
set directed true
set weighted true

# Create pentagon vertices in a circle
circle 5 radius 200 start P

# Connect as pentagram (skip-one pattern)
edge P1 -> P3 weight 2
edge P3 -> P5 weight 2
edge P5 -> P2 weight 2
edge P2 -> P4 weight 2
edge P4 -> P1 weight 2

# Add outer pentagon
edge P1 <-> P2 weight 1
edge P2 <-> P3 weight 1
edge P3 <-> P4 weight 1
edge P4 <-> P5 weight 1
edge P5 <-> P1 weight 1

layout circle
print ★ Pentagram Complete ★


# ───────────────────────────────────────────────────────────────
# 2. THE FLOWER OF LIFE (Geometric Pattern)
# ───────────────────────────────────────────────────────────────
clear

# Center circle
circle 6 radius 100 start C

# Connect center to all petals
edge C1 <-> C2 weight 1
edge C2 <-> C3 weight 1
edge C3 <-> C4 weight 1
edge C4 <-> C5 weight 1
edge C5 <-> C6 weight 1
edge C6 <-> C1 weight 1

# Add outer ring
circle 12 radius 250 start O

# Connect outer ring
cycle iter i in 1..12 weight 1

layout spring
print ✿ Flower of Life Complete ✿


# ───────────────────────────────────────────────────────────────
# 3. THE HYPERCUBE (4D Projection)
# ───────────────────────────────────────────────────────────────
clear

# Inner cube
node A1 at 250 200
node A2 at 350 200
node A3 at 350 300
node A4 at 250 300
node B1 at 270 220
node B2 at 330 220
node B3 at 330 280
node B4 at 270 280

# Outer cube
node C1 at 200 150
node C2 at 400 150
node C3 at 400 350
node C4 at 200 350
node D1 at 240 180
node D2 at 360 180
node D3 at 360 320
node D4 at 240 320

# Inner cube edges
edge A1 <=> A2 weight 1
edge A2 <=> A3 weight 1
edge A3 <=> A4 weight 1
edge A4 <=> A1 weight 1
edge B1 <=> B2 weight 1
edge B2 <=> B3 weight 1
edge B3 <=> B4 weight 1
edge B4 <=> B1 weight 1
edge A1 <=> B1 weight 1
edge A2 <=> B2 weight 1
edge A3 <=> B3 weight 1
edge A4 <=> B4 weight 1

# Outer cube edges
edge C1 <=> C2 weight 2
edge C2 <=> C3 weight 2
edge C3 <=> C4 weight 2
edge C4 <=> C1 weight 2
edge D1 <=> D2 weight 2
edge D2 <=> D3 weight 2
edge D3 <=> D4 weight 2
edge D4 <=> D1 weight 2
edge C1 <=> D1 weight 2
edge C2 <=> D2 weight 2
edge C3 <=> D3 weight 2
edge C4 <=> D4 weight 2

# Connecting edges between cubes
edge A1 -> C1 weight 3
edge A2 -> C2 weight 3
edge A3 -> C3 weight 3
edge A4 -> C4 weight 3
edge B1 -> D1 weight 3
edge B2 -> D2 weight 3
edge B3 -> D3 weight 3
edge B4 -> D4 weight 3

print ◈ Hypercube (Tesseract) Complete ◈


# ───────────────────────────────────────────────────────────────
# 4. THE GALAXY (Spiral Pattern)
# ───────────────────────────────────────────────────────────────
clear
set directed false

# Create spiral arms using iter
iter i in 1..20: node S{i} at 400 300
iter i in 1..20: node M{i} at 400 300
iter i in 1..20: node L{i} at 400 300

# Center
node CORE at 400 300

# Connect spiral arms
path iter i in 1..20 weight 1
path iter i in 1..20 weight 1
path iter i in 1..20 weight 1

# Connect to core
edge CORE -> S1 weight 3
edge CORE -> M1 weight 3
edge CORE -> L1 weight 3

layout spring
print ≛ Galaxy Spiral Complete ≛


# ───────────────────────────────────────────────────────────────
# 5. THE NEURAL NETWORK (Layered Graph)
# ───────────────────────────────────────────────────────────────
clear
set directed true
set weighted true

# Input layer (5 nodes)
iter i in 1..5: node I{i} at 100 200

# Hidden layer 1 (8 nodes)
iter i in 1..8: node H1{i} at 250 200

# Hidden layer 2 (8 nodes)
iter i in 1..8: node H2{i} at 400 200

# Output layer (3 nodes)
iter i in 1..3: node O{i} at 550 200

# Connect layers (simplified - just show pattern)
edge I1 -> H11 weight 1
edge I1 -> H12 weight 1
edge I2 -> H12 weight 1
edge I2 -> H13 weight 1
edge H11 -> H21 weight 2
edge H12 -> H21 weight 2
edge H12 -> H22 weight 2
edge H21 -> O1 weight 3
edge H22 -> O1 weight 3
edge H22 -> O2 weight 3

layout spring
print ◉ Neural Network Complete ◉


# ───────────────────────────────────────────────────────────────
# 6. THE MANDALA (Radial Symmetry)
# ───────────────────────────────────────────────────────────────
clear
set directed false

# Multiple concentric circles
circle 8 radius 80 start R1
circle 12 radius 150 start R2
circle 16 radius 220 start R3
circle 20 radius 290 start R4

# Connect rings radially
edge R11 -> R21 weight 1
edge R13 -> R24 weight 1
edge R15 -> R27 weight 1
edge R17 -> R210 weight 1

edge R21 -> R31 weight 2
edge R24 -> R35 weight 2
edge R27 -> R39 weight 2
edge R210 -> R313 weight 2

edge R31 -> R41 weight 3
edge R35 -> R46 weight 3
edge R39 -> R411 weight 3
edge R313 -> R416 weight 3

# Ring connections
cycle iter i in 1..8 weight 1
cycle iter i in 1..12 weight 1
cycle iter i in 1..16 weight 1
cycle iter i in 1..20 weight 1

layout circle
print ࿇ Mandala Complete ࿇


# ───────────────────────────────────────────────────────────────
# 7. THE INFINITY LADDER (Möbius-like)
# ───────────────────────────────────────────────────────────────
clear
set directed true

# Create two parallel ladder rows
ladder A 6 weight 1

# Add curved connections for infinity effect
curve A1a A1b 30
curve A2a A2b -30
curve A3a A3b 30
curve A4a A4b -30
curve A5a A5b 30
curve A6a A6b -30

print ∞ Infinity Ladder Complete ∞


# ───────────────────────────────────────────────────────────────
# 8. THE COMPLETE KAGOME (Japanese Basket Weave)
# ───────────────────────────────────────────────────────────────
clear
set directed false

# Create triangular lattice pattern
star C1 T1 T2 T3 T4 T5 T6
star C2 T2 T3 T7 T8 T9 T10

# Connect triangles
edge T1 -- T2 weight 1
edge T2 -- T3 weight 1
edge T3 -- T4 weight 1
edge T4 -- T5 weight 1
edge T5 -- T6 weight 1
edge T6 -- T1 weight 1

layout spring
print ⌾ Kagome Weave Complete ⌾


# ═══════════════════════════════════════════════════════════════
# End of Beautiful Graphs Collection
# Run individual sections or the entire file!
# ═══════════════════════════════════════════════════════════════
