import os
from pathlib import Path
from artifacts import generate_mira_artifact

out_dir = Path("/home/helton/AnaliseTextos/app/test_mira_output")
out_dir.mkdir(exist_ok=True)

(out_dir / "06_sintese_parecer.md").write_text("NOTA: 8.5\nDECISÃO FINAL: Minor Revisions\n", encoding="utf-8")
(out_dir / "01_metodologia.md").write_text("Metodologia baseada em revisão sistemática de literatura seguindo as diretrizes PRISMA, com busca nas bases Scopus e Web of Science.", encoding="utf-8")
(out_dir / "04_gaps_logicos.md").write_text("1. Ausência de grupo controle adequado para validar os resultados.\n2. Amostra pequena limitando a generalização (n=15).\n3. Viés de seleção na fase de recrutamento.", encoding="utf-8")

generate_mira_artifact(out_dir, "Teste Paper")
print(f"Gerado em {out_dir / 'apresentacao_animada.html'}")
