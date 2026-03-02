#!/usr/bin/env python3
"""Test curvature calculation for parallel edges."""

import math

# Simulate the curvature calculation logic
def test_curvature():
    # Test case: 2 parallel edges (even)
    num_parallel = 2
    spacing = 30.0
    
    print("=== 2 Parallel Edges ===")
    for edge_idx in range(num_parallel):
        if num_parallel % 2 == 1:
            parallel_offset = (edge_idx - num_parallel // 2) * spacing
        else:
            parallel_offset = (edge_idx - (num_parallel - 1) / 2) * spacing
        curvature = (edge_idx - (num_parallel - 1) / 2) * 60.0
        
        print(f"Edge {edge_idx}: offset={parallel_offset}, curvature={curvature}")
    
    # Test case: 3 parallel edges (odd)
    print("\n=== 3 Parallel Edges ===")
    num_parallel = 3
    for edge_idx in range(num_parallel):
        if num_parallel % 2 == 1:
            parallel_offset = (edge_idx - num_parallel // 2) * spacing
        else:
            parallel_offset = (edge_idx - (num_parallel - 1) / 2) * spacing
        curvature = (edge_idx - (num_parallel - 1) / 2) * 60.0
        
        print(f"Edge {edge_idx}: offset={parallel_offset}, curvature={curvature}")
    
    # Test case: bidirectional (1 edge each direction)
    print("\n=== Bidirectional (1 each way) ===")
    num_parallel = 1
    is_bidirectional = True
    curvature = 0.0
    if num_parallel > 1:
        curvature = 42  # won't execute
    if is_bidirectional:
        if curvature == 0:
            curvature = 40.0
    print(f"Forward edge: curvature={curvature}")

if __name__ == "__main__":
    test_curvature()
