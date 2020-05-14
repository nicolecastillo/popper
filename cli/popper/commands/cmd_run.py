import click
import os
import traceback

from popper import log as logging
from popper.cli import log, pass_context
from popper.config import ConfigLoader
from popper.parser import WorkflowParser
from popper.runner import WorkflowRunner


@click.command("run", short_help="Run a workflow or step.")
@click.argument("step", required=False)
@click.option(
    "-f",
    "--wfile",
    help="File containing the definition of the workflow.",
    required=True,
)
@click.option(
    "-d",
    "--debug",
    help=("Generate detailed messages of what popper does (overrides --quiet)"),
    required=False,
    is_flag=True,
)
@click.option(
    "--dry-run",
    help="Do not run the workflow, only print what would be executed.",
    required=False,
    is_flag=True,
)
@click.option(
    "--log-file",
    help="Path to a log file. No log is created if this is not given.",
    required=False,
)
@click.option(
    "-q",
    "--quiet",
    help="Do not print output generated by steps.",
    required=False,
    is_flag=True,
)
@click.option(
    "--reuse",
    help="Reuse containers between executions (persist container state).",
    required=False,
    is_flag=True,
)
@click.option(
    "-e",
    "--engine",
    help="Specify runtime for executing the workflow.",
    type=click.Choice(["docker", "singularity", "vagrant"]),
)
@click.option(
    "-r",
    "--resource-manager",
    help="Specify resource manager for executing the workflow.",
    type=click.Choice(["host", "slurm"]),
)
@click.option(
    "--skip",
    help=("Skip the given step (can be given multiple times)."),
    required=False,
    default=list(),
    hidden=True,
    multiple=True,
)
@click.option(
    "--skip-clone",
    help="Skip cloning repositories (assume they have been cloned).",
    required=False,
    is_flag=True,
)
@click.option(
    "--skip-pull",
    help="Skip pulling container images (assume they exist in local cache).",
    required=False,
    is_flag=True,
)
@click.option(
    "--substitution",
    help=("A key-value pair defining a substitution. " "Can be given multiple times."),
    required=False,
    default=list(),
    multiple=True,
)
@click.option(
    "--allow-loose",
    help="Do not throw an error if a substitution variable passed as an "
    "argument is unused in the workflow definition.",
    required=False,
    is_flag=True,
)
@click.option(
    "-w",
    "--workspace",
    help="Path to workspace folder.",
    required=False,
    show_default=False,
    default=os.getcwd(),
)
@click.option(
    "-c", "--conf", help="Path to file with configuration options.", required=False
)
@pass_context
def cli(
    ctx,
    step,
    wfile,
    debug,
    dry_run,
    log_file,
    quiet,
    reuse,
    engine,
    resource_manager,
    skip,
    skip_pull,
    skip_clone,
    substitution,
    allow_loose,
    workspace,
    conf,
):
    """Runs a Popper workflow. Only executes STEP if given.

    To specify a container engine to use other than docker, use the --engine/-e
    flag. For executing on a resource manager such as SLURM or Kubernetes, use
    the --resource-manager/-r flag. Alternatively, a configuration file can be
    given (--conf flag) that can specify container options, resource manager
    options, or both (see "Workflow Syntax and Execution Runtime" section of
    the Popper documentation for more).

    If the container engine (-e) or resource manager (-r) are specified with a
    flag and a configuration file is given as well, the values passed via the
    flags are given preference over those contained in the configuration file.
    """
    # set the logging levels.
    level = "STEP_INFO"
    if quiet:
        level = "INFO"
    if debug:
        level = "DEBUG"
    log.setLevel(level)

    if dry_run:
        logging.msg_prefix = "DRYRUN: "

    if log_file:
        # also log to a file
        logging.add_log(log, log_file)

    # check conflicting flags and fail if needed
    if skip and step:
        log.fail("`--skip` can not be used when STEP argument is passed.")

    # invoke wf factory; handles formats, validations, filtering
    wf = WorkflowParser.parse(
        wfile,
        step=step,
        skipped_steps=skip,
        substitutions=substitution,
        allow_loose=allow_loose,
    )

    config = ConfigLoader.load(
        engine_name=engine,
        resman_name=resource_manager,
        config_file=conf,
        reuse=reuse,
        dry_run=dry_run,
        skip_pull=skip_pull,
        skip_clone=skip_clone,
        workspace_dir=workspace,
    )

    with WorkflowRunner(config) as runner:
        try:
            runner.run(wf)
        except Exception as e:
            log.debug(traceback.format_exc())
            log.fail(e)
