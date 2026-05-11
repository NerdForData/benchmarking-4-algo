import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.cm as cm
import numpy as np


class GanttChart:
    """
    Gantt chart renderer for JSP schedules.

    - Each job gets a distinct colour (colourblind-friendly tab20 palette)
    - Gridlines and axis formatting for readability
    - Operation label includes job AND operation index (J2-O1 instead of just J2)
    - Legend maps colours to job indices
    - Figure size scales with number of machines so labels don't overlap
    - savefig support: pass output_path to save instead of (or in addition to) showing
    """

    @staticmethod
    def plot(schedule, title="Schedule", output_path=None, show=True):
        if not schedule:
            print("Empty schedule — nothing to plot.")
            return

        machines = sorted(set(op["machine"] for op in schedule))
        jobs = sorted(set(op["job"] for op in schedule))

        n_machines = len(machines)
        n_jobs = len(jobs)

        # Colour palette — tab20 gives 20 distinct colours; cycle for larger instances
        cmap = cm.get_cmap("tab20", n_jobs)
        job_colours = {job_id: cmap(i) for i, job_id in enumerate(jobs)}

        fig_height = max(4, n_machines * 0.55 + 2)
        fig, ax = plt.subplots(figsize=(16, fig_height))

        for op in schedule:
            colour = job_colours[op["job"]]
            ax.barh(
                y=op["machine"],
                width=op["duration"],
                left=op["start"],
                color=colour,
                edgecolor="white",
                linewidth=0.5,
                align="center",
                height=0.6,
            )
            # Label: show job + operation index, centred in the bar
            label = f"J{op['job']}-O{op['operation']}"
            bar_centre = op["start"] + op["duration"] / 2
            ax.text(
                bar_centre,
                op["machine"],
                label,
                ha="center",
                va="center",
                fontsize=7,
                color="white",
                fontweight="bold",
                clip_on=True,
            )

        # Axes formatting
        ax.set_yticks(machines)
        ax.set_yticklabels([f"M{m}" for m in machines], fontsize=9)
        ax.set_xlabel("Time", fontsize=10)
        ax.set_ylabel("Machine", fontsize=10)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.grid(axis="x", linestyle="--", linewidth=0.4, alpha=0.7)
        ax.set_axisbelow(True)

        # Makespan line
        makespan = max(op["end"] for op in schedule)
        ax.axvline(x=makespan, color="red", linestyle=":", linewidth=1.2, label=f"Makespan = {makespan}")

        # Legend for jobs
        legend_patches = [
            mpatches.Patch(color=job_colours[j], label=f"Job {j}")
            for j in jobs
        ]
        # Keep legend manageable for large instances
        if n_jobs <= 20:
            ax.legend(
                handles=legend_patches + [
                    mpatches.Patch(color="none", label=""),  # spacer
                ],
                loc="upper left",
                bbox_to_anchor=(1.01, 1),
                borderaxespad=0,
                fontsize=8,
                frameon=True,
                title="Jobs",
                title_fontsize=9,
            )

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            print(f"Gantt chart saved to {output_path}")

        if show:
            plt.show()

        plt.close(fig)