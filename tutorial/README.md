# Testing Hardware Circuits using Fault

Welcome to the **fault tutorial**. The sources for these files are hosted in
the [GitHub
repository](https://github.com/leonardt/fault/tree/master/tutorial), please
submit issues using the [GH issue
tracker](https://github.com/leonardt/fault/issues).  Pull requests with typo
fixes and other improvements are always welcome!

## Overview
The *fault* library abstracts circuit testing actions using Python objects.

Underlying the fault framework is
[magma](https://github.com/phanrahan/magma), a library that abstracts circuits
as Python objects.  Magma provides the ability to define circuits in Python,
wrap existing circuits from `verilog`, or create designs combining both.
Fault's features are agnostic to how the `magma.Circuit` object is defined,
which means that you can use it with your existing `verilog` designs by using
magma's `DefineFromVerilog` feature.

Fault is designed as an embedded DSL, which enables the construction of *test
generators* using standard Python programming techniques.  A *test generator*
is a program that consumes a set of parameters to produce a test or suite of
tests for a specific instance of a *chip generator*.  A *chip generator* is a
program that consumes a set of parameters to produce a *chip* (an instance of
the chip generator).

Fault is designed to provide a unified interface for describing circuit tests
in Python.  

* Abstract circuit testing in Python (integration with magma)
* Metaprogram tests (flexibility, parametrization, HW generators)
* Leverage Python libraries: pytest (also, constrained random number generators)
* Reuse (standard OOP)
* Simulation and formal (future plans: emulation and bringup)
* (plans) Coverage

## Tester Abstraction
### Exercise 1

## pytest Parametrization
### Exercise 2

## Assume/Guarantee
### Exercise 3

# Fault Internals
This section provides an introduction to the internal architecture of the fault
system.  The goal is to provide the required knowledge for anyone interested in
contributing bug fixes, features, or refactors to the fault codebase.  The
fault API docs are hosted at
[http://truong.io/fault/](http://truong.io/fault/), this is a valuable link to
remember.

## Testers
### SimulationTester
### SymbolicTester

## Targets
### Verilator
### SystemVerilog
### CoSA

## Roadmap
### Simulation Actions
### Constrained Random
### Formal
