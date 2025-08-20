"""SWHID validation command-line tool."""

import sys
from pathlib import Path
from typing import Optional

import click

from src2id.core.swhid import SWHIDGenerator


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--expected-swhid",
    help="Expected SWHID to compare against",
)
@click.option(
    "--use-fallback",
    is_flag=True,
    help="Use fallback implementation instead of swh.model",
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Verbose output",
)
def validate_swhid(
    path: Path,
    expected_swhid: Optional[str],
    use_fallback: bool,
    verbose: bool,
) -> None:
    """Validate SWHID generation for a directory or file.
    
    This tool generates a SWHID for the given PATH and optionally
    compares it against an expected value.
    """
    generator = SWHIDGenerator(use_swh_model=not use_fallback)
    
    # Determine if path is file or directory
    if path.is_file():
        generated_swhid = generator.generate_content_swhid(path)
        path_type = "file"
    else:
        generated_swhid = generator.generate_directory_swhid(path)
        path_type = "directory"
    
    # Output generated SWHID
    click.echo(f"Generated SWHID for {path_type} '{path.name}':")
    click.echo(f"  {generated_swhid}")
    
    if verbose:
        click.echo(f"\nImplementation: {'fallback' if use_fallback else 'swh.model'}")
        click.echo(f"Path: {path.absolute()}")
        
        if path.is_dir():
            # Count files
            file_count = sum(1 for _ in path.rglob("*") if _.is_file())
            click.echo(f"Files in directory: {file_count}")
    
    # Validate format
    if generator.validate_swhid(generated_swhid):
        click.echo("✓ Valid SWHID format")
    else:
        click.echo("✗ Invalid SWHID format", err=True)
        sys.exit(1)
    
    # Compare with expected if provided
    if expected_swhid:
        click.echo(f"\nExpected SWHID:")
        click.echo(f"  {expected_swhid}")
        
        if generated_swhid == expected_swhid:
            click.echo("✓ SWHIDs match!")
        else:
            click.echo("✗ SWHIDs do not match", err=True)
            
            # Show difference
            gen_parts = generated_swhid.split(":")
            exp_parts = expected_swhid.split(":")
            
            if len(gen_parts) == 4 and len(exp_parts) == 4:
                if gen_parts[2] != exp_parts[2]:
                    click.echo(f"  Type mismatch: {gen_parts[2]} vs {exp_parts[2]}")
                if gen_parts[3] != exp_parts[3]:
                    click.echo(f"  Hash mismatch: {gen_parts[3]} vs {exp_parts[3]}")
            
            sys.exit(1)


if __name__ == "__main__":
    validate_swhid()