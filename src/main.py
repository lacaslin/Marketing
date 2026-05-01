"""MIMO CLI — Cross-border E-commerce Multilingual Marketing Content Factory."""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.config import config
from src.models.product import ProductInput
from src.orchestrator import PipelineOrchestrator, save_pipeline_output
from src.utils.image import discover_images
from src.utils.logger import setup_logger, log

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="mimo")
def cli():
    """MIMO — Multilingual Marketing Content Factory for Cross-border E-commerce.

    Transforms Chinese product data + images into SEO-optimized, culturally adapted
    marketing copy for Amazon, Shopify, TikTok, and more across 8 languages.
    """


@cli.command()
@click.option("--product", "-p", required=True, help="Product name in Chinese")
@click.option("--specs", "-s", default="", help="Product specifications")
@click.option("--price", default="", help="Price range or MSRP")
@click.option("--feature", "-f", "features", multiple=True, help="Key feature (repeatable)")
@click.option("--category", "-c", default="", help="Product category")
@click.option("--brand", "-b", default="", help="Brand name")
@click.option("--images", "-i", default="", help="Directory containing product images (jpg/png/webp)")
@click.option("--locales", "-l", default="", help="Target locales, comma-separated (fr,de,es,ja,ko,pt,it,ar). Default: all")
@click.option("--platform", "-t", "platforms", default="", help="Target platforms, comma-separated (amazon,shopify,tiktok). Default: all")
@click.option("--output", "-o", default="", help="Output directory (default: ./output)")
@click.option("--dry-run", is_flag=True, help="Stop after review stage, skip CMS publish")
def run(product, specs, price, features, category, brand, images, locales, platforms, output, dry_run):
    """Run the full content factory pipeline for a product."""
    logger = setup_logger(level=config.log_level)

    # Validate config
    issues = config.validate()
    if issues:
        for issue in issues:
            console.print(f"[red]Config Error:[/red] {issue}")
        if any("ANTHROPIC_API_KEY" in i for i in issues):
            console.print("\n[yellow]Set your API key:[/yellow] export ANTHROPIC_API_KEY=sk-ant-...")
            sys.exit(1)

    # Parse inputs
    locale_list = [l.strip() for l in locales.split(",") if l.strip()] if locales else []
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()] if platforms else []
    output_dir = Path(output) if output else config.output_dir

    # Discover images
    image_paths = []
    if images:
        try:
            found = discover_images(images)
            image_paths = [str(p) for p in found]
            console.print(f"[green]Found {len(image_paths)} image(s)[/green] in {images}")
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] {e}")

    # Build product input
    product_input = ProductInput(
        name=product,
        specs=specs,
        price=price,
        features=list(features),
        category=category,
        brand=brand,
    )

    # Display summary
    console.print(Panel.fit(
        f"[bold]Product:[/bold] {product}\n"
        f"[bold]Images:[/bold] {len(image_paths)}\n"
        f"[bold]Locales:[/bold] {', '.join(locale_list) or 'all (8)'}\n"
        f"[bold]Platforms:[/bold] {', '.join(platform_list) or 'all (3)'}\n"
        f"[bold]Mode:[/bold] {'Dry run (no publish)' if dry_run else 'Full pipeline'}",
        title="MIMO Content Factory",
        border_style="cyan",
    ))

    # Run pipeline
    orchestrator = PipelineOrchestrator(config)

    async def _run():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Running pipeline...", total=None)
            result = await orchestrator.run(
                product=product_input,
                image_paths=image_paths,
                locales=locale_list,
                platforms=platform_list,
            )
            progress.update(task, completed=True)
        return result

    result = asyncio.run(_run())

    # Display results
    _display_results(result)

    # Save output
    files = save_pipeline_output(result, output_dir)
    console.print(f"\n[green]Output saved to:[/green] {output_dir.absolute()} ({len(files)} files)")

    if result.errors:
        console.print("\n[red]Errors encountered:[/red]")
        for e in result.errors:
            console.print(f"  - {e}")


@cli.command()
def list_locales():
    """List supported locales and languages."""
    table = Table(title="Supported Locales")
    table.add_column("Code", style="cyan")
    table.add_column("Language", style="green")
    for code, name in config.languages.items():
        table.add_row(code, name)
    console.print(table)


@cli.command()
def list_platforms():
    """List supported platforms."""
    table = Table(title="Supported Platforms")
    table.add_column("Platform", style="cyan")
    for name in config.platforms:
        table.add_row(name)
    console.print(table)


def _display_results(result):
    """Display pipeline results in a rich table."""
    console.print(f"\n[bold]Pipeline completed in {result.total_time_seconds:.1f}s[/bold]")

    # Localized content summary
    table = Table(title="Localized Content")
    table.add_column("Locale", style="cyan")
    table.add_column("Platform", style="green")
    table.add_column("Title", style="white")
    table.add_column("Status", style="yellow")

    for loc in result.localized:
        locale = loc.get("locale", "?")
        platform = loc.get("platform", "?")
        title = (loc.get("title") or "")[:50]
        status = loc.get("status", "draft")

        review = next((r for r in result.reviews if r.get("locale") == locale and r.get("platform") == platform), None)
        if review:
            status = "PASSED" if review.get("passed") else "FAILED"
            status_style = "green" if review.get("passed") else "red"
        else:
            status_style = "white"

        table.add_row(locale, platform, title, f"[{status_style}]{status}[/{status_style}]")

    console.print(table)


if __name__ == "__main__":
    cli()
