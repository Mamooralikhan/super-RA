# 🧰 Claude Skills for RAs: Replication & Research Workflows

Actively developed and maintained.  
A collection of Claude skills that make research assistant work faster, more reproducible, and easier to train across projects.

---

## 🎯 What this repo is for

This repo focuses on Claude skills - prompts and configurations you can load into Claude Code - that help RAs:

- Build and maintain replication packages.
- Structure and document empirical projects.
- Run analysis, QA, and documentation steps in a consistent way.

You describe the task. The skill guides Claude through planning, implementing, checking, and documenting the work.

---

## 🧩 What is a “Claude skill” here?

In this repo, a skill is:

- A focused Claude configuration (system prompts, rules, patterns).
- Designed for a specific RA task, such as:
  - Creating a replication package.
  - Auditing code and reproducibility.
  - Drafting documentation or referee-facing notes.
- Written so that RAs can invoke it with a short natural language description of their project.

Each skill is meant to be:

- **Reusable** across projects.
- **Opinionated** about best practices.
- **Transparent** about what it will and will not do.

---

## 📦 First skills in this repo

Planned initial skills (names and details may change as you iterate):

- **/create-replication-package**  
  Proposes a project structure, organizes raw / intermediate / final data, and drafts instructions for running all code from scratch.

- **/analyze-dataset**  
  Helps RAs move from a high-level research question to a concrete analysis plan, with checks for identification, specification, and diagnostics.

- **/audit-reproducibility**  
  Reviews an existing project for missing pieces in the replication chain - scripts, seeds, data transformations, and documentation.

- **/draft-ra-notes**  
  Summarizes what was done in a project (and why) so PIs, coauthors, and future RAs can quickly understand the workflow.

Update this list as you add or rename skills.

---

## 🚀 How to use these skills

1. **Open Claude Code** with your project repo or folder in context.
2. **Load the relevant skill**:
   - Paste the skill prompt into a new session, or
   - Use your own skill-loading setup if you have one.
3. **Describe your task** in 2–3 sentences:
   - What project you are working on.
   - Where the data and code live.
   - What output you need (replication package, analysis plan, QA, documentation).
4. **Let the skill run**:
   - Claude will propose a plan, ask clarifying questions if needed, and execute the steps it is configured for.
5. **Commit and iterate**:
   - Review the changes locally.
   - Commit only what you are comfortable owning in version control.

---

## 🧪 Example workflows

Some ways an RA might use this repo:

- You receive a partially organized project folder and need a journal-ready replication package.  
  Use `/create-replication-package` to propose structure, scripts, and documentation.

- You inherit a codebase with unclear diagnostics and robustness checks.  
  Use `/analyze-dataset` to sketch an analysis and diagnostics plan.

- You are preparing a project for sharing with a coauthor or external collaborator.  
  Use `/audit-reproducibility` to identify missing steps in the pipeline.

Replace these with concrete examples from your own projects over time.

---

## 🗺️ Roadmap

Tentative roadmap for this repo:

- More skills for:
  - Data validation and consistency checks.
  - Code style and review checklists.
  - Advanced replication workflows (multi-country, multi-wave data).
- Example configurations for:
  - Stata-heavy projects.
  - R / Python pipelines.
  - Mixed-tool environments typical in policy and development work.

As you test these skills with RAs, update the roadmap to reflect what actually works.

---

## 🤝 Contributing

Contributions and suggestions are welcome.

- **Issues**  
  Use GitHub Issues to report bugs, request new skills, or suggest changes to existing prompts.

- **Pull requests**  
  Add a new skill, refine instructions, or contribute examples of how you used these skills in real projects.

- **Documentation**  
  If you adapt a skill to a new institutional context or data environment, consider documenting it so others can learn from your setup.

---

## 📜 License

Add your preferred license here (for example: MIT, GPL, or a custom license) so others know how they can use, modify, and distribute these Claude skills.
