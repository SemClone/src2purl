"""Detect and identify multiple subcomponents in a project."""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class Subcomponent:
    """Represents a detected subcomponent in a project."""
    path: Path
    type: str  # 'npm', 'python', 'rust', 'go', 'java', 'mono', 'multi'
    name: Optional[str] = None
    markers: List[str] = None
    
    def __post_init__(self):
        if self.markers is None:
            self.markers = []


class SubcomponentDetector:
    """Detects multiple subcomponents in a project structure."""
    
    # Package markers that indicate a component boundary
    PACKAGE_MARKERS = {
        'package.json': 'npm',
        'pyproject.toml': 'python',
        'setup.py': 'python',
        'requirements.txt': 'python',
        'Cargo.toml': 'rust',
        'go.mod': 'go',
        'pom.xml': 'java',
        'build.gradle': 'java',
        'build.gradle.kts': 'java',
        'Gemfile': 'ruby',
        'composer.json': 'php',
        'CMakeLists.txt': 'cmake',
        'Makefile': 'make',
        '.csproj': 'dotnet',
        'mix.exs': 'elixir',
    }
    
    # Directories that typically indicate subcomponents
    SUBCOMPONENT_PATTERNS = {
        'packages/*': 'monorepo',  # Lerna/Yarn workspaces
        'apps/*': 'monorepo',      # Nx/Turborepo
        'services/*': 'microservices',
        'libs/*': 'libraries',
        'modules/*': 'modules',
        'components/*': 'components',
        'plugins/*': 'plugins',
        'extensions/*': 'extensions',
    }
    
    def __init__(self, verbose: bool = False):
        """Initialize the detector."""
        self.verbose = verbose
    
    def detect_subcomponents(
        self,
        root_path: Path,
        max_depth: int = 3
    ) -> List[Subcomponent]:
        """
        Detect all subcomponents in a project.
        
        Args:
            root_path: Root directory to scan
            max_depth: Maximum depth to search for subcomponents
            
        Returns:
            List of detected subcomponents
        """
        subcomponents = []
        visited = set()
        
        # Check if root itself is a component
        root_markers = self._check_markers(root_path)
        if root_markers:
            root_component = Subcomponent(
                path=root_path,
                type=self._determine_type(root_markers),
                name=root_path.name,
                markers=root_markers
            )
            subcomponents.append(root_component)
            visited.add(root_path)
        
        # Search for nested subcomponents
        self._scan_for_subcomponents(
            root_path,
            subcomponents,
            visited,
            current_depth=0,
            max_depth=max_depth
        )
        
        # Deduplicate and organize
        subcomponents = self._organize_subcomponents(subcomponents)
        
        if self.verbose:
            self._print_detection_results(subcomponents)
        
        return subcomponents
    
    def _scan_for_subcomponents(
        self,
        path: Path,
        subcomponents: List[Subcomponent],
        visited: set,
        current_depth: int,
        max_depth: int
    ):
        """Recursively scan for subcomponents."""
        if current_depth >= max_depth:
            return
        
        try:
            for item in path.iterdir():
                if item.is_dir() and item not in visited:
                    # Skip common non-component directories
                    if item.name in {'.git', '__pycache__', 'node_modules', 
                                   'venv', 'build', 'dist', '.idea', '.vscode'}:
                        continue
                    
                    # Check for package markers
                    markers = self._check_markers(item)
                    
                    if markers:
                        # Found a subcomponent
                        component = Subcomponent(
                            path=item,
                            type=self._determine_type(markers),
                            name=item.name,
                            markers=markers
                        )
                        subcomponents.append(component)
                        visited.add(item)
                        
                        # Don't scan inside detected components by default
                        # unless it's a monorepo pattern
                        if self._is_monorepo_pattern(item):
                            self._scan_for_subcomponents(
                                item, subcomponents, visited,
                                current_depth + 1, max_depth
                            )
                    else:
                        # Continue scanning subdirectories
                        self._scan_for_subcomponents(
                            item, subcomponents, visited,
                            current_depth + 1, max_depth
                        )
        except PermissionError:
            pass
    
    def _check_markers(self, path: Path) -> List[str]:
        """Check for package markers in a directory."""
        markers = []
        
        for marker_file, _ in self.PACKAGE_MARKERS.items():
            marker_path = path / marker_file
            if marker_path.exists():
                markers.append(marker_file)
        
        return markers
    
    def _determine_type(self, markers: List[str]) -> str:
        """Determine component type from markers."""
        types = set()
        for marker in markers:
            if marker in self.PACKAGE_MARKERS:
                types.add(self.PACKAGE_MARKERS[marker])
        
        if len(types) == 1:
            return list(types)[0]
        elif len(types) > 1:
            return 'multi'
        else:
            return 'unknown'
    
    def _is_monorepo_pattern(self, path: Path) -> bool:
        """Check if this looks like a monorepo."""
        # Check for workspace configuration files
        workspace_files = [
            'lerna.json',
            'nx.json',
            'pnpm-workspace.yaml',
            'rush.json',
            'turbo.json'
        ]
        
        for ws_file in workspace_files:
            if (path / ws_file).exists():
                return True
        
        # Check for packages/apps directories
        monorepo_dirs = {'packages', 'apps', 'services', 'libs'}
        subdirs = {item.name for item in path.iterdir() if item.is_dir()}
        
        return bool(monorepo_dirs & subdirs)
    
    def _organize_subcomponents(
        self,
        subcomponents: List[Subcomponent]
    ) -> List[Subcomponent]:
        """Organize and deduplicate subcomponents."""
        # Remove duplicates based on path
        seen_paths = set()
        unique_components = []
        
        for comp in subcomponents:
            if comp.path not in seen_paths:
                unique_components.append(comp)
                seen_paths.add(comp.path)
        
        # Sort by path depth (root first, then nested)
        unique_components.sort(key=lambda c: len(c.path.parts))
        
        return unique_components
    
    def _print_detection_results(self, subcomponents: List[Subcomponent]):
        """Print detected subcomponents in a nice table."""
        if not subcomponents:
            console.print("[yellow]No subcomponents detected[/yellow]")
            return
        
        table = Table(title=f"Detected {len(subcomponents)} Subcomponents")
        table.add_column("Path", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Markers", style="yellow")
        
        for comp in subcomponents:
            # Try to get relative path, fallback to absolute
            try:
                rel_path = str(comp.path.relative_to(Path.cwd()))
            except ValueError:
                # If not relative to cwd, just use the path as-is
                rel_path = str(comp.path)
            
            markers_str = ", ".join(comp.markers[:3])
            if len(comp.markers) > 3:
                markers_str += f" +{len(comp.markers)-3}"
            
            table.add_row(rel_path, comp.type, markers_str)
        
        console.print(table)


async def identify_subcomponents(
    root_path: Path,
    max_depth: int = 3,
    confidence_threshold: float = 0.5,
    verbose: bool = False,
    use_swh: bool = False
) -> Dict[str, Any]:
    """
    Identify all subcomponents in a project.
    
    Args:
        root_path: Root directory to analyze
        max_depth: Maximum depth for scanning
        confidence_threshold: Minimum confidence for identification
        verbose: Enable verbose output
        use_swh: Include Software Heritage checking
        
    Returns:
        Dictionary with identification results for all subcomponents
    """
    from src2id.search import identify_source
    
    # Detect subcomponents
    detector = SubcomponentDetector(verbose=verbose)
    subcomponents = detector.detect_subcomponents(root_path, max_depth)
    
    if not subcomponents:
        # No subcomponents detected, identify as single project
        if verbose:
            console.print("[dim]No subcomponents detected, analyzing as single project[/dim]")
        
        result = await identify_source(
            path=root_path,
            max_depth=max_depth,
            confidence_threshold=confidence_threshold,
            verbose=verbose,
            use_swh=use_swh
        )
        
        return {
            "root": root_path,
            "subcomponents": [],
            "single_result": result
        }
    
    # Identify each subcomponent
    results = {
        "root": root_path,
        "subcomponents": [],
        "total_identified": 0,
        "total_components": len(subcomponents)
    }
    
    if verbose:
        console.print(f"\n[bold]Identifying {len(subcomponents)} subcomponents...[/bold]\n")
    
    for i, comp in enumerate(subcomponents, 1):
        if verbose:
            console.print(f"[cyan]Component {i}/{len(subcomponents)}: {comp.path.name}[/cyan]")
        
        # Identify this component
        comp_result = await identify_source(
            path=comp.path,
            max_depth=1,  # Don't go too deep for subcomponents
            confidence_threshold=confidence_threshold,
            verbose=False,  # Less verbose for individual components
            use_swh=use_swh
        )
        
        # Add component info to result
        comp_info = {
            "path": str(comp.path),
            "type": comp.type,
            "markers": comp.markers,
            "identified": comp_result["identified"],
            "confidence": comp_result["confidence"],
            "repository": comp_result.get("final_origin"),
            "strategies_used": comp_result.get("strategies_used", [])
        }
        
        results["subcomponents"].append(comp_info)
        
        if comp_result["identified"]:
            results["total_identified"] += 1
            
        if verbose:
            if comp_result["identified"]:
                console.print(f"  ✓ Identified: {comp_result['final_origin']}")
            else:
                console.print(f"  ✗ Not identified")
    
    # Print summary
    if verbose:
        console.print(f"\n[bold green]Summary:[/bold green]")
        console.print(f"Total components: {results['total_components']}")
        console.print(f"Identified: {results['total_identified']}")
        console.print(f"Success rate: {results['total_identified']/results['total_components']:.1%}")
    
    return results