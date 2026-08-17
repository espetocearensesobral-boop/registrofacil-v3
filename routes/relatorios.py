from csv import writer
from io import StringIO

from flask import Blueprint, Response, render_template, request, jsonify, url_for

from models import executar_query, listar_processos, obter_tipos_servico, obter_status_processo_config
from routes.auth import login_status_required, proteger_input
from routes.permissoes import permission_required


relatorios_bp = Blueprint("relatorios", __name__, url_prefix="/relatorios")


def _count(table):
    row = executar_query(f"SELECT COUNT(*) AS total FROM {table}", fetch_one=True)
    return int(row["total"] if row else 0)


def _paginate(total, pagina, por_pagina):
    pagina = max(int(pagina or 1), 1)
    por_pagina = min(max(int(por_pagina or 25), 10), 100)
    total_paginas = (total + por_pagina - 1) // por_pagina
    return pagina, por_pagina, total_paginas, (pagina - 1) * por_pagina


@relatorios_bp.route("/", methods=["GET"])
@login_status_required
@permission_required("relatorios_geral")
def index():
    indicadores = {
        "processos": _count("processos"),
        "titulares": _count("titulares"),
        "apresentantes": _count("apresentantes"),
        "servicos": _count("tipos_servico"),
        "contatos_sem_telefone": int(executar_query(
            """SELECT COUNT(*) AS total FROM (
                   SELECT id FROM titulares WHERE telefone IS NULL OR TRIM(telefone) = ''
                   UNION ALL
                   SELECT id FROM apresentantes WHERE telefone IS NULL OR TRIM(telefone) = ''
               )""",
            fetch_one=True,
        )["total"]),
        "contatos_sem_email": int(executar_query(
            """SELECT COUNT(*) AS total FROM (
                   SELECT id FROM titulares WHERE email IS NULL OR TRIM(email) = ''
                   UNION ALL
                   SELECT id FROM apresentantes WHERE email IS NULL OR TRIM(email) = ''
               )""",
            fetch_one=True,
        )["total"]),
    }
    return render_template("relatorios/index.html", indicadores=indicadores)


@relatorios_bp.route("/processos/dados", methods=["GET"])
@login_status_required
@permission_required("relatorios_geral")
def processos_dados():
    """Fornece a listagem do modal de relatório de processos."""
    filtros = {
        "busca": proteger_input(request.args.get("busca", "").strip()),
        "matricula": proteger_input(request.args.get("matricula", "").strip()),
    }
    tipo = request.args.get("tipo", type=int)
    status = request.args.get("status", type=int)
    if tipo:
        filtros["tipo"] = tipo
    if status:
        filtros["status_id"] = status

    pagina = max(request.args.get("pagina", 1, type=int), 1)
    por_pagina = min(max(request.args.get("por_pagina", 25, type=int), 10), 100)
    resultado = listar_processos(filtros, pagina, por_pagina, "id_desc")
    processos = []
    for processo in resultado["processos"] or []:
        item = dict(processo)
        item["imprimir_url"] = url_for("processos.gerar_relatorio_customizado", processo_id=item["id"], tipo="html_print")
        item["baixar_url"] = url_for("processos.gerar_pdf", processo_id=item["id"])
        processos.append(item)
    return jsonify({
        "success": True,
        "processos": processos,
        "total": resultado["total_records"],
        "pagina": pagina,
        "total_paginas": resultado["total_pages"],
        "tipos": [dict(row) for row in (obter_tipos_servico() or [])],
        "status": [dict(row) for row in (obter_status_processo_config() or [])],
    })


@relatorios_bp.route("/contatos", methods=["GET"])
@login_status_required
@permission_required("relatorios_geral")
def contatos():
    busca = proteger_input(request.args.get("busca", "").strip())
    origem = request.args.get("origem", "todos")
    if origem not in {"todos", "titulares", "apresentantes"}:
        origem = "todos"

    partes = []
    params = []
    if origem in {"todos", "titulares"}:
        partes.append("SELECT 'Titular' AS origem, id, nome, telefone, email FROM titulares")
    if origem in {"todos", "apresentantes"}:
        partes.append("SELECT 'Apresentante' AS origem, id, nome, telefone, email FROM apresentantes")
    base = " UNION ALL ".join(partes)
    where = ""
    if busca:
        where = " WHERE nome LIKE ? OR telefone LIKE ? OR email LIKE ?"
        termo = f"%{busca}%"
        params.extend([termo, termo, termo])

    count_row = executar_query(
        f"SELECT COUNT(*) AS total FROM ({base}) contatos{where}",
        params,
        fetch_one=True,
    )
    total = int(count_row["total"] if count_row else 0)
    pagina, por_pagina, total_paginas, offset = _paginate(
        total, request.args.get("pagina", 1, type=int), request.args.get("por_pagina", 25, type=int)
    )
    if request.args.get("imprimir"):
        rows = executar_query(
            f"SELECT origem, id, nome, telefone, email FROM ({base}) contatos{where} ORDER BY nome COLLATE NOCASE ASC",
            params,
            fetch_all=True,
        ) or []
        return render_template("relatorios/contatos_print.html", contatos=rows, busca=busca, origem=origem, total=total)
    rows = executar_query(
        f"SELECT origem, id, nome, telefone, email FROM ({base}) contatos{where} ORDER BY nome COLLATE NOCASE ASC LIMIT ? OFFSET ?",
        params + [por_pagina, offset],
        fetch_all=True,
    ) or []
    return render_template(
        "relatorios/contatos.html",
        contatos=rows,
        busca=busca,
        origem=origem,
        pagina=pagina,
        por_pagina=por_pagina,
        total=total,
        total_paginas=total_paginas,
    )


@relatorios_bp.route("/contatos/exportar", methods=["GET"])
@login_status_required
@permission_required("relatorios_exportar")
def exportar_contatos():
    busca = proteger_input(request.args.get("busca", "").strip())
    origem = request.args.get("origem", "todos")
    if origem not in {"todos", "titulares", "apresentantes"}:
        origem = "todos"
    partes = []
    params = []
    if origem in {"todos", "titulares"}:
        partes.append("SELECT 'Titular' AS origem, nome, telefone, email FROM titulares")
    if origem in {"todos", "apresentantes"}:
        partes.append("SELECT 'Apresentante' AS origem, nome, telefone, email FROM apresentantes")
    base = " UNION ALL ".join(partes)
    where = ""
    if busca:
        where = " WHERE nome LIKE ? OR telefone LIKE ? OR email LIKE ?"
        termo = f"%{busca}%"
        params.extend([termo, termo, termo])
    rows = executar_query(
        f"SELECT origem, nome, telefone, email FROM ({base}) contatos{where} ORDER BY nome COLLATE NOCASE ASC",
        params,
        fetch_all=True,
    ) or []
    stream = StringIO()
    csv_writer = writer(stream)
    csv_writer.writerow(["Origem", "Nome", "Telefone", "E-mail"])
    csv_writer.writerows([[row["origem"], row["nome"], row["telefone"] or "", row["email"] or ""] for row in rows])
    return Response(
        "\ufeff" + stream.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=relatorio_contatos.csv"},
    )


@relatorios_bp.route("/servicos", methods=["GET"])
@login_status_required
@permission_required("relatorios_geral")
def servicos():
    rows = executar_query(
        """SELECT ts.id, ts.nome, ts.descricao, ts.prazo_padrao, ts.ativo,
                  COUNT(p.id) AS total_processos
             FROM tipos_servico ts
             LEFT JOIN processos p ON p.tipo_id = ts.id
            GROUP BY ts.id, ts.nome, ts.descricao, ts.prazo_padrao, ts.ativo
            ORDER BY ts.ativo DESC, ts.nome COLLATE NOCASE ASC""",
        fetch_all=True,
    ) or []
    if request.args.get("imprimir"):
        return render_template("relatorios/servicos_print.html", servicos=rows)
    return render_template("relatorios/servicos.html", servicos=rows)


@relatorios_bp.route("/servicos/exportar", methods=["GET"])
@login_status_required
@permission_required("relatorios_exportar")
def exportar_servicos():
    rows = executar_query(
        """SELECT ts.nome, ts.descricao, ts.prazo_padrao, ts.ativo,
                  COUNT(p.id) AS total_processos
             FROM tipos_servico ts
             LEFT JOIN processos p ON p.tipo_id = ts.id
            GROUP BY ts.id, ts.nome, ts.descricao, ts.prazo_padrao, ts.ativo
            ORDER BY ts.ativo DESC, ts.nome COLLATE NOCASE ASC""",
        fetch_all=True,
    ) or []
    stream = StringIO()
    csv_writer = writer(stream)
    csv_writer.writerow(["Serviço", "Descrição", "Prazo padrão", "Status", "Processos"])
    csv_writer.writerows([
        [row["nome"], row["descricao"] or "", row["prazo_padrao"] or 0,
         "Ativo" if row["ativo"] else "Inativo", row["total_processos"]]
        for row in rows
    ])
    return Response(
        "\ufeff" + stream.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=relatorio_servicos.csv"},
    )
