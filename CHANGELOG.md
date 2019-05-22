# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.10]
### Fixed
- https://github.com/leonardt/fault/pull/107 fixes a bug in how SV integer
  literals are generated

## [2.0.10]
### Fixed
- Fixes bug in tester.compile

## [2.0.9]
### Fixed
- Fixes bug related to char promotion in verilator backend

## [2.0.8]
### Added
- https://github.com/leonardt/fault/pull/96 adds support for
  `fault.config.set_test_dir`. Call with 'callee_file_dir' to have the
  `directory` parameter to `compile_and_run` relative to the calling file
  (default is relative to where Python is invoked)
- Adds support for poking `fault.AnyValue` (X) using the `"system-verilog"`
  target
- https://github.com/leonardt/fault/pull/102 Adds support for more options for
  `"ncsim"` simulator
    - Adds switch to suppress warnings.
    - Adds switch to dump VCD
    - Adds parameter to specify the number of cycles
- https://github.com/leonardt/fault/pull/98 Adds support for file i/o for
  system verilog targets

### Fixed
- https://github.com/leonardt/fault/pull/99 fixes a bug for equality checks
- https://github.com/leonardt/fault/pull/100 fixes a bug for checking the
  status code of verilator commands
- https://github.com/leonardt/fault/pull/101 fixes a bug for expect/poke of
  signed values

## [2.0.7]
### Added
- Adds support for loop and file i/o actions
- Added ability to skip verilator compile using `VerilatorTarget`

### Changes
- Changed print action interface to match standard `printf` interface (ala C)


## [2.0.4]
### Fixes
- Fixes issue with handling wide signals (greater than 32 bits).

## [2.0.1]
### Fixes
- Fixes for upstream changes to magma `Array` and `Bits` type constructor
  syntax.

## [2.0.0]
### Changes
- Updates to using hwtypes and uses the new hwtypes syntax

## [1.0.8]
### Fixes
- Fixes issue with tests that use setattr only for top interface ports. In this
  case, the top circuit header does not need to be included for debug signals.

## [1.0.7]
### Fixes
- Fixes backwards compatability issues with verilator

## [1.0.6]
### Fixes
- Fixes verilator version guard for top circuit prefix
- Fixes support for poking coreir_arst register

## [1.0.5]
### Fixes
- Fixes verilator version guard for including top circuit header

## [1.0.4]
### Added
- Adds support for arrays and tuples in setattr interface

## [1.0.3]
### Fixed
- Fixed bug in .sv file logic for VerilogTarget

## [1.0.2]
### Added
- Added support for .sv files to VerilogTarget

## [1.0.1]
### Fixed
- Fixed functional tester's use of self.circuit which was not updated for the
  new Tester setattr interface

## 1.0.0
### Added
- Added preliminary support for peek and expect on internal signals and poke on
  internal registers

[Unreleased]: https://github.com/leonardt/fault/compare/v1.0.8...HEAD
[1.0.7]: https://github.com/leonardt/fault/compare/v1.0.7...v1.0.8
[1.0.7]: https://github.com/leonardt/fault/compare/v1.0.6...v1.0.7
[1.0.6]: https://github.com/leonardt/fault/compare/v1.0.5...v1.0.6
[1.0.5]: https://github.com/leonardt/fault/compare/v1.0.4...v1.0.5
[1.0.4]: https://github.com/leonardt/fault/compare/v1.0.3...v1.0.4
[1.0.3]: https://github.com/leonardt/fault/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/leonardt/fault/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/leonardt/fault/compare/v1.0.0...v1.0.1
