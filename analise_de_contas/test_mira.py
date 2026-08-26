import os
from pathlib import Path
from artifacts import generate_mira_artifact

out_dir = Path("/home/helton/AnaliseContas/app/test_mira_output")
out_dir.mkdir(exist_ok=True)

(out_dir / "06_parecer_final.md").write_text(
    "NOTA GERAL: 7.5\nDECISÃO: Aprovado com Ressalvas\n\n"
    "## Pontos Positivos\n1. Balanço de receitas bem estruturado\n"
    "2. Fundo de reserva com saldo adequado\n",
    encoding="utf-8",
)
(out_dir / "01_receitas.md").write_text(
    "Receitas condominiais: taxa mensal R$ 45.000, fundo de reserva R$ 2.250, "
    "multas R$ 1.800, aluguéis salão R$ 800.",
    encoding="utf-8",
)
(out_dir / "04_consistencia_financeira.md").write_text(
    "1. Divergência no rateio: unidade 101 com fração 2,5% mas pago R$ 1.200 (deveria ser R$ 1.125).\n"
    "2. Fundo de manutenção com saldo negativo não explicado.\n"
    "3. Despesa de energia com aumento de 35% sem justificativa.",
    encoding="utf-8",
)

generate_mira_artifact(out_dir, "Teste Condomínio")
print(f"Gerado em {out_dir / 'apresentacao_animada.html'}")
