"""
tests/test_adaptive_scheduler.py
"""
import pytest
from resource_engine.resource_budget import ResourceBudget, ExecutionPolicy

def test_lower_cpu_budget_reduces_workers():
    budget_perf = ResourceBudget.from_policy(ExecutionPolicy.PERFORMANCE)
    budget_low = ResourceBudget.from_policy(ExecutionPolicy.LOW_CPU)
    
    cores_available = 16
    
    workers_perf = budget_perf.effective_workers(cores_available)
    workers_low = budget_low.effective_workers(cores_available)
    
    assert workers_perf > workers_low
    assert workers_perf == 16
    assert workers_low == max(1, int(16 * 0.25))

def test_custom_cpu_budget_override():
    budget = ResourceBudget(cpu_budget_cores=2.5)
    assert budget.effective_workers(16) == 2
    assert budget.effective_workers(1) == 1
