# Subcomponent Detection and Identification

## Overview

The tool now supports detecting and identifying **multiple subcomponents** within a project. This is essential for:
- **Monorepos** - Projects with multiple packages (Lerna, Nx, Turborepo)
- **Multi-language projects** - Mixed Python/JavaScript/Rust components
- **Microservices** - Multiple service directories
- **Plugin architectures** - Main app + multiple plugins

## How It Works

### 1. Detection Phase
The detector scans for package markers that indicate component boundaries:

| Marker File | Component Type |
|------------|---------------|
| `package.json` | Node.js/npm |
| `pyproject.toml`, `setup.py` | Python |
| `Cargo.toml` | Rust |
| `go.mod` | Go |
| `pom.xml`, `build.gradle` | Java |
| `Gemfile` | Ruby |
| `composer.json` | PHP |
| `CMakeLists.txt` | CMake/C++ |

### 2. Identification Phase
Each detected subcomponent is identified separately using the optimized strategy order:
1. Hash Search
2. Web Search  
3. SCANOSS
4. SWH (optional)

## Usage

### CLI Usage

```bash
# Detect and identify all subcomponents
swhpi /path/to/project --detect-subcomponents

# With specific options
swhpi /path/to/project \
  --detect-subcomponents \
  --max-depth 3 \
  --confidence-threshold 0.5 \
  --verbose
```

### API Usage

```python
from swhpi.core.subcomponent_detector import identify_subcomponents

results = await identify_subcomponents(
    root_path=Path("test_data"),
    max_depth=3,
    confidence_threshold=0.5,
    verbose=True
)

# Results contain:
# - List of all detected subcomponents
# - Identification results for each
# - Success statistics
```

## Example Output

```
$ swhpi test_data --detect-subcomponents

Detected 3 Subcomponents
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Path                    Type    Markers
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
test_data/darktable     cmake   CMakeLists.txt
test_data/scanoss_py    python  pyproject.toml, setup.py
test_data/tempo/scanner python  pyproject.toml
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Identifying 3 subcomponents...

Component 1/3: darktable
  ✓ Identified: https://github.com/darktable-org/darktable

Component 2/3: scanoss_py
  ✓ Identified: https://github.com/scanoss/scanoss.py

Component 3/3: scanner
  ✓ Identified: https://github.com/swh/scanner

Summary:
Total components: 3
Identified: 3
Success rate: 100%
```

## Monorepo Support

The detector recognizes common monorepo patterns:

### Lerna/Yarn Workspaces
```
project/
├── package.json         # Root package
├── lerna.json          # Monorepo marker
└── packages/
    ├── package-a/      # Subcomponent 1
    │   └── package.json
    └── package-b/      # Subcomponent 2
        └── package.json
```

### Nx/Turborepo
```
project/
├── nx.json             # Monorepo marker
├── apps/
│   ├── web/           # Subcomponent 1
│   └── api/           # Subcomponent 2
└── libs/
    └── shared/        # Subcomponent 3
```

## Benefits

### 1. Accurate Identification
- Each component identified with its specific repository
- No confusion between main project and dependencies
- Better match accuracy for multi-component projects

### 2. License Compliance
- Identify licenses for each subcomponent
- Track different licenses in mixed projects
- Better SBOM generation

### 3. Dependency Analysis
- Understand the full dependency tree
- Identify shared vs unique dependencies
- Better security scanning

## Performance Considerations

### Optimizations
- Components identified in parallel when possible
- Caching applies to each subcomponent
- Early termination if confidence threshold met

### Limits
- Default max 100 files per component
- Configurable depth limit (default 3)
- Skips common non-source directories

## API Reference

### SubcomponentDetector Class

```python
detector = SubcomponentDetector(verbose=True)
subcomponents = detector.detect_subcomponents(
    root_path=Path("project"),
    max_depth=3
)
```

### Subcomponent Model

```python
@dataclass
class Subcomponent:
    path: Path           # Component directory
    type: str           # 'npm', 'python', 'rust', etc.
    name: Optional[str] # Component name
    markers: List[str]  # Package files found
```

### identify_subcomponents Function

```python
results = await identify_subcomponents(
    root_path: Path,
    max_depth: int = 3,
    confidence_threshold: float = 0.5,
    verbose: bool = False,
    use_swh: bool = False
)
```

Returns:
```python
{
    "root": Path,
    "total_components": int,
    "total_identified": int,
    "subcomponents": [
        {
            "path": str,
            "type": str,
            "markers": List[str],
            "identified": bool,
            "confidence": float,
            "repository": str,
            "strategies_used": List[str]
        }
    ]
}
```

## Future Enhancements

1. **Dependency Graph** - Show relationships between components
2. **Version Detection** - Extract version from package files
3. **Language-specific** - Better detection for specific ecosystems
4. **CI/CD Integration** - Output for different CI systems
5. **SBOM Export** - Generate proper SBOM with all components