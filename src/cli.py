"""CLI interface for domain finder."""

import json
import click
import logging
import warnings
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from typing import List, Optional

# Suppress noisy library warnings/errors (socket, whois, dns)
warnings.filterwarnings("ignore")
logging.getLogger("whois").setLevel(logging.CRITICAL)
logging.getLogger("dns").setLevel(logging.CRITICAL)

from .generators import DictionaryGenerator, PhoneticGenerator, CompoundGenerator
from .checkers import AvailabilityService
from .scoring import DomainScorer
from .utils import WordValidator
from .utils.results_store import ResultsStore


console = Console()


def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load configuration from YAML file."""
    import yaml
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file) as f:
            return yaml.safe_load(f)
    return {}


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """OpenDomains - Find underrated available domain names."""
    pass


@cli.command()
@click.option('--dictionary/--no-dictionary', default=True, help='Use dictionary words')
@click.option('--phonetic/--no-phonetic', default=True, help='Generate phonetic words')
@click.option('--compound/--no-compound', default=True, help='Generate compound words')
@click.option('--count', '-n', default=100, help='Number of words to generate per type')
@click.option('--output', '-o', default=None, help='Output file (JSON)')
@click.option('--min-length', default=4, help='Minimum word length')
@click.option('--max-length', default=10, help='Maximum word length')
def generate(dictionary, phonetic, compound, count, output, min_length, max_length):
    """Generate word candidates for domains."""
    all_words = set()
    
    with console.status("[bold green]Generating words..."):
        if dictionary:
            gen = DictionaryGenerator(min_length=min_length, max_length=max_length)
            words = gen.generate(limit=count)
            curated = gen.generate_curated()
            all_words.update(words)
            all_words.update(curated)
            console.print(f"[green]Dictionary:[/green] {len(words)} words + {len(curated)} curated")
        
        if phonetic:
            gen = PhoneticGenerator(min_length=min_length, max_length=max_length)
            words = gen.generate(count=count)
            all_words.update(words)
            console.print(f"[green]Phonetic:[/green] {len(words)} words")
        
        if compound:
            gen = CompoundGenerator(max_length=max_length + 5)
            words = gen.generate_all()
            all_words.update(words)
            console.print(f"[green]Compound:[/green] {len(words)} words")
    
    console.print(f"\n[bold]Total unique words:[/bold] {len(all_words)}")
    
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(sorted(list(all_words)), f, indent=2)
        console.print(f"[green]Saved to {output}[/green]")
    else:
        # Print sample
        sample = sorted(list(all_words))[:20]
        console.print("\n[bold]Sample words:[/bold]")
        console.print(", ".join(sample))


@cli.command()
@click.argument('words', nargs=-1)
@click.option('--wordlist', '-w', default=None, help='Path to wordlist file')
@click.option('--tlds', '-t', default='com,io,ai', help='TLDs to check (comma-separated)')
@click.option('--verify/--no-verify', default=True, help='Verify with WHOIS')
@click.option('--output', '-o', default=None, help='Output file (JSON)')
@click.option('--min-score', default=0, help='Minimum score to include')
def check(words, wordlist, tlds, verify, output, min_score):
    """Check domain availability."""
    tld_list = [t.strip() for t in tlds.split(',')]
    
    # Collect words
    word_list = list(words)
    if wordlist:
        with open(wordlist) as f:
            content = f.read()
            try:
                word_list.extend(json.loads(content))
            except json.JSONDecodeError:
                word_list.extend(line.strip() for line in content.splitlines() if line.strip())
    
    if not word_list:
        console.print("[red]No words provided. Use arguments or --wordlist[/red]")
        return
    
    console.print(f"[bold]Checking {len(word_list)} words across {len(tld_list)} TLDs...[/bold]")
    
    service = AvailabilityService()
    scorer = DomainScorer()
    store = ResultsStore()
    
    available_domains = []
    all_results_to_store = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        total = len(word_list) * len(tld_list)
        cache_task = progress.add_task("[cyan]Cache lookup...", total=total)
        dns_task = progress.add_task("[blue]DNS check...", total=0, visible=False)
        whois_task = progress.add_task("[yellow]WHOIS verify...", total=0, visible=False)
        
        phase_totals = {}
        
        def update_phase(phase, current, phase_total):
            if phase == 'cache':
                progress.update(cache_task, completed=current)
                if current == phase_total:
                    progress.update(cache_task, visible=False)
            elif phase == 'dns':
                if phase not in phase_totals:
                    phase_totals['dns'] = phase_total
                    progress.update(dns_task, total=phase_total, visible=True)
                progress.update(dns_task, completed=current)
                if current == phase_total:
                    progress.update(dns_task, visible=False)
            elif phase == 'whois':
                if phase not in phase_totals:
                    phase_totals['whois'] = phase_total
                    progress.update(whois_task, total=phase_total, visible=True)
                progress.update(whois_task, completed=current)
        
        # Get ALL results, not just available ones
        domains = [f"{word}.{tld}" for word in word_list for tld in tld_list]
        results = service.check_batch(
            domains,
            verify_with_whois=verify,
            phase_callback=update_phase
        )
        
        for result in results:
            score = scorer.score(result.domain)
            score_dict = {
                "total_score": score.total_score,
                "pronounceability": score.pronounceability,
                "spellability": score.spellability,
                "length_score": score.length_score,
                "memorability": score.memorability,
                "brandability": score.brandability,
                "dictionary_score": score.dictionary_score,
                "tld_multiplier": score.tld_multiplier
            }
            
            # Store all results
            all_results_to_store.append({
                "domain": result.domain,
                "available": result.available,
                "method": result.method,
                "error": result.error,
                "score": score_dict
            })
            
            if result.available and score.total_score >= min_score:
                available_domains.append({
                    'domain': result.domain,
                    'score': score.total_score,
                    'breakdown': score.to_dict()['breakdown'],
                    'method': result.method,
                    'cached': result.cached
                })
    
    # Store all results to SQLite
    store.add_batch(all_results_to_store)
    console.print(f"[dim]Stored {len(all_results_to_store)} results to database[/dim]")
    
    # Sort by score
    available_domains.sort(key=lambda x: x['score'], reverse=True)
    
    # Display results
    if available_domains:
        table = Table(title="Available Domains")
        table.add_column("Domain", style="cyan")
        table.add_column("Score", justify="right", style="green")
        table.add_column("Pronounce", justify="right")
        table.add_column("Spell", justify="right")
        table.add_column("Length", justify="right")
        table.add_column("Method", style="dim")
        
        for d in available_domains[:50]:  # Show top 50
            table.add_row(
                d['domain'],
                f"{d['score']:.1f}",
                str(d['breakdown']['pronounceability']),
                str(d['breakdown']['spellability']),
                str(d['breakdown']['length']),
                d['method']
            )
        
        console.print(table)
        console.print(f"\n[bold green]Found {len(available_domains)} available domains![/bold green]")
        
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(available_domains, f, indent=2)
            console.print(f"[green]Saved to {output}[/green]")
    else:
        console.print("[yellow]No available domains found.[/yellow]")


@cli.command()
@click.option('--tlds', '-t', default='com,io,ai,co', help='TLDs to check')
@click.option('--count', '-n', default=200, help='Number of words to generate')
@click.option('--min-score', default=70, help='Minimum score threshold')
@click.option('--output', '-o', default='data/results/available_domains.json', help='Output file')
@click.option('--verify/--no-verify', default=True, help='Verify with WHOIS')
def hunt(tlds, count, min_score, output, verify):
    """Full pipeline: generate, check, score, and find gems."""
    tld_list = [t.strip() for t in tlds.split(',')]
    
    console.print("[bold]Starting domain hunt...[/bold]\n")
    
    # Generate words
    all_words = set()
    
    with console.status("[bold green]Generating word candidates..."):
        dict_gen = DictionaryGenerator()
        all_words.update(dict_gen.generate(limit=count))
        all_words.update(dict_gen.generate_curated())
        
        phon_gen = PhoneticGenerator()
        all_words.update(phon_gen.generate(count=count))
        
        comp_gen = CompoundGenerator()
        all_words.update(comp_gen.generate_all())
    
    console.print(f"[green]Generated {len(all_words)} unique word candidates[/green]\n")
    
    # Check availability
    service = AvailabilityService()
    scorer = DomainScorer()
    store = ResultsStore()
    word_list = list(all_words)
    
    available_domains = []
    all_results_to_store = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        total = len(word_list) * len(tld_list)
        cache_task = progress.add_task("[cyan]Cache lookup...", total=total)
        dns_task = progress.add_task("[blue]DNS check...", total=0, visible=False)
        whois_task = progress.add_task("[yellow]WHOIS verify...", total=0, visible=False)
        
        phase_totals = {}
        
        def update_phase(phase, current, phase_total):
            if phase == 'cache':
                progress.update(cache_task, completed=current)
                if current == phase_total:
                    progress.update(cache_task, visible=False)
            elif phase == 'dns':
                if phase not in phase_totals:
                    phase_totals['dns'] = phase_total
                    progress.update(dns_task, total=phase_total, visible=True)
                progress.update(dns_task, completed=current)
                if current == phase_total:
                    progress.update(dns_task, visible=False)
            elif phase == 'whois':
                if phase not in phase_totals:
                    phase_totals['whois'] = phase_total
                    progress.update(whois_task, total=phase_total, visible=True)
                progress.update(whois_task, completed=current)
        
        # Get ALL results, not just available ones
        domains = [f"{word}.{tld}" for word in word_list for tld in tld_list]
        results = service.check_batch(
            domains,
            verify_with_whois=verify,
            phase_callback=update_phase
        )
        
        for result in results:
            score = scorer.score(result.domain)
            score_dict = {
                "total_score": score.total_score,
                "pronounceability": score.pronounceability,
                "spellability": score.spellability,
                "length_score": score.length_score,
                "memorability": score.memorability,
                "brandability": score.brandability,
                "dictionary_score": score.dictionary_score,
                "tld_multiplier": score.tld_multiplier
            }
            
            # Store all results
            all_results_to_store.append({
                "domain": result.domain,
                "available": result.available,
                "method": result.method,
                "error": result.error,
                "score": score_dict
            })
            
            if result.available and score.total_score >= min_score:
                available_domains.append({
                    'domain': result.domain,
                    'score': score.total_score,
                    'breakdown': score.to_dict()['breakdown'],
                    'method': result.method
                })
    
    # Store all results to SQLite
    store.add_batch(all_results_to_store)
    console.print(f"[dim]Stored {len(all_results_to_store)} results to database[/dim]")
    
    # Sort and categorize
    available_domains.sort(key=lambda x: x['score'], reverse=True)
    
    gems = [d for d in available_domains if d['score'] >= 85]
    good = [d for d in available_domains if 75 <= d['score'] < 85]
    decent = [d for d in available_domains if d['score'] < 75]
    
    # Display results
    console.print("\n")
    
    if gems:
        console.print("[bold yellow]GEMS (Score 85+):[/bold yellow]")
        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("Domain", style="cyan bold")
        table.add_column("Score", justify="right", style="green bold")
        for d in gems[:20]:
            table.add_row(d['domain'], f"{d['score']:.1f}")
        console.print(table)
    
    if good:
        console.print("\n[bold blue]GOOD (Score 75-84):[/bold blue]")
        console.print(", ".join(d['domain'] for d in good[:30]))
    
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Gems: {len(gems)}")
    console.print(f"  Good: {len(good)}")
    console.print(f"  Decent: {len(decent)}")
    console.print(f"  [bold green]Total available: {len(available_domains)}[/bold green]")
    
    # Save results
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump({
                'gems': gems,
                'good': good,
                'decent': decent,
                'summary': {
                    'total_checked': len(word_list) * len(tld_list),
                    'total_available': len(available_domains),
                    'gems_count': len(gems),
                    'good_count': len(good)
                }
            }, f, indent=2)
        console.print(f"\n[green]Results saved to {output}[/green]")


@cli.command()
@click.argument('domain')
def score(domain):
    """Score a single domain."""
    scorer = DomainScorer()
    result = scorer.score(domain)
    
    console.print(f"\n[bold]Domain:[/bold] {domain}")
    console.print(f"[bold green]Total Score:[/bold green] {result.total_score:.1f}")
    console.print(f"\n[bold]Breakdown:[/bold]")
    console.print(f"  Pronounceability: {result.pronounceability}/100")
    console.print(f"  Spellability:     {result.spellability}/100")
    console.print(f"  Length:           {result.length_score}/100")
    console.print(f"  Memorability:     {result.memorability}/100")
    console.print(f"  Brandability:     {result.brandability}/100")
    console.print(f"  Dictionary:       {result.dictionary_score}/100")
    console.print(f"  TLD Multiplier:   {result.tld_multiplier}x")


@cli.command()
@click.option('--available/--all', default=True, help='Show only available domains')
@click.option('--min-score', default=0, help='Minimum score filter')
@click.option('--tld', default=None, help='Filter by TLD')
@click.option('--limit', '-n', default=50, help='Number of results to show')
@click.option('--export', '-e', default=None, help='Export to CSV file')
def results(available, min_score, tld, limit, export):
    """Query and analyze stored domain results."""
    store = ResultsStore()
    
    # Get stats first
    stats = store.stats()
    
    console.print("\n[bold]Database Statistics:[/bold]")
    console.print(f"  Total domains checked: {stats['total']}")
    console.print(f"  Available: [green]{stats['available']}[/green]")
    console.print(f"  Unavailable: [red]{stats['unavailable']}[/red]")
    console.print(f"  Unknown: [yellow]{stats['unknown']}[/yellow]")
    
    if stats['with_scores'] > 0:
        console.print(f"\n[bold]Score Stats (available):[/bold]")
        console.print(f"  Average: {stats['avg_score']}")
        console.print(f"  Best: {stats['max_score']}")
        console.print(f"  Worst: {stats['min_score']}")
    
    if stats['tlds']:
        console.print(f"\n[bold]TLD Breakdown:[/bold]")
        for t, counts in sorted(stats['tlds'].items(), key=lambda x: x[1]['total'], reverse=True)[:10]:
            console.print(f"  .{t}: {counts['total']} checked, [green]{counts['available']}[/green] available")
    
    # Query domains
    domains = store.query(
        available=True if available else None,
        min_score=min_score if min_score > 0 else None,
        tld=tld,
        limit=limit
    )
    
    if domains:
        console.print(f"\n[bold]Top {len(domains)} Domains:[/bold]")
        table = Table()
        table.add_column("Domain", style="cyan")
        table.add_column("Score", justify="right", style="green")
        table.add_column("Dict", justify="right")
        table.add_column("Avail", justify="center")
        table.add_column("Method", style="dim")
        
        for d in domains:
            avail_icon = "[green]Y[/green]" if d['available'] == 1 else "[red]N[/red]" if d['available'] == 0 else "[yellow]?[/yellow]"
            score_str = f"{d['total_score']:.1f}" if d['total_score'] else "-"
            dict_str = str(d['dictionary_score']) if d['dictionary_score'] else "-"
            table.add_row(d['domain'], score_str, dict_str, avail_icon, d['method'] or "-")
        
        console.print(table)
    
    if export:
        count = store.export_csv(export, available_only=available)
        console.print(f"\n[green]Exported {count} domains to {export}[/green]")


def main():
    cli()


if __name__ == '__main__':
    main()
