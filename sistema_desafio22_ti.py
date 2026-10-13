"""
Sistema de Gestão - Desafio TI
==============================

Aplicação desktop (Python + CustomTkinter) com três módulos:

1. Comissões : consolida vendas por vendedor e calcula comissões por faixa.
2. Estoque   : registra entradas/saídas, valida regras e mantém histórico.
3. Juros     : calcula juros simples (2,5% ao dia) sobre títulos vencidos.

Estrutura do arquivo
--------------------
- Dados do desafio (JSON)
- Regras de negócio  (sem nenhuma dependência de interface, fáceis de testar)
- Componentes visuais reutilizáveis
- Páginas (uma por módulo)
- Janela principal

Requisitos: Python 3.9+ e `pip install customtkinter`
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional, Sequence, Union

# ==========================================================================
# DADOS DO DESAFIO (JSONs originais)
# ==========================================================================
DADOS_VENDAS = {
    "vendas": [
        {"vendedor": "João Silva", "valor": 1200.50}, {"vendedor": "João Silva", "valor": 950.75},
        {"vendedor": "João Silva", "valor": 1800.00}, {"vendedor": "João Silva", "valor": 1400.30},
        {"vendedor": "João Silva", "valor": 1100.90}, {"vendedor": "João Silva", "valor": 1550.00},
        {"vendedor": "João Silva", "valor": 1700.80}, {"vendedor": "João Silva", "valor": 250.30},
        {"vendedor": "João Silva", "valor": 480.75}, {"vendedor": "João Silva", "valor": 320.40},
        {"vendedor": "Maria Souza", "valor": 2100.40}, {"vendedor": "Maria Souza", "valor": 1350.60},
        {"vendedor": "Maria Souza", "valor": 950.20}, {"vendedor": "Maria Souza", "valor": 1600.75},
        {"vendedor": "Maria Souza", "valor": 1750.00}, {"vendedor": "Maria Souza", "valor": 1450.90},
        {"vendedor": "Maria Souza", "valor": 400.50}, {"vendedor": "Maria Souza", "valor": 180.20},
        {"vendedor": "Maria Souza", "valor": 90.75}, {"vendedor": "Carlos Oliveira", "valor": 800.50},
        {"vendedor": "Carlos Oliveira", "valor": 1200.00}, {"vendedor": "Carlos Oliveira", "valor": 1950.30},
        {"vendedor": "Carlos Oliveira", "valor": 1750.80}, {"vendedor": "Carlos Oliveira", "valor": 1300.60},
        {"vendedor": "Carlos Oliveira", "valor": 300.40}, {"vendedor": "Carlos Oliveira", "valor": 500.00},
        {"vendedor": "Carlos Oliveira", "valor": 125.75}, {"vendedor": "Ana Lima", "valor": 1000.00},
        {"vendedor": "Ana Lima", "valor": 1100.50}, {"vendedor": "Ana Lima", "valor": 1250.75},
        {"vendedor": "Ana Lima", "valor": 1400.20}, {"vendedor": "Ana Lima", "valor": 1550.90},
        {"vendedor": "Ana Lima", "valor": 1650.00}, {"vendedor": "Ana Lima", "valor": 75.30},
        {"vendedor": "Ana Lima", "valor": 420.90}, {"vendedor": "Ana Lima", "valor": 315.40},
    ]
}

DADOS_ESTOQUE = {
    "estoque": [
        {"codigoProduto": 101, "descricaoProduto": "Caneta Azul", "estoque": 150},
        {"codigoProduto": 102, "descricaoProduto": "Caderno Universitário", "estoque": 75},
        {"codigoProduto": 103, "descricaoProduto": "Borracha Branca", "estoque": 200},
        {"codigoProduto": 104, "descricaoProduto": "Lápis Preto HB", "estoque": 320},
        {"codigoProduto": 105, "descricaoProduto": "Marcador de Texto Amarelo", "estoque": 90},
    ]
}

# ==========================================================================
# REGRAS DE NEGÓCIO (sem interface)
# ==========================================================================
LIMITE_SEM_COMISSAO = Decimal("100.00")   # abaixo disso: 0%
LIMITE_COMISSAO_BAIXA = Decimal("500.00")  # abaixo disso: 1% | a partir daqui: 5%
TAXA_COMISSAO_BAIXA = Decimal("0.01")
TAXA_COMISSAO_ALTA = Decimal("0.05")
TAXA_JUROS_DIARIA = Decimal("0.025")       # 2,5% ao dia (juros simples)
ESTOQUE_BAIXO = 100                        # abaixo disso o produto recebe o alerta "Baixo"
CENTAVOS = Decimal("0.01")


class ErroValidacao(ValueError):
    """Erro de regra de negócio ou de entrada de dados, com mensagem pronta para o usuário."""


def arredondar(valor: Decimal) -> Decimal:
    """Arredonda para centavos (meio para cima), evitando erros de ponto flutuante."""
    return valor.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def formatar_brl(valor: Decimal) -> str:
    """Formata no padrão brasileiro: R$ 1.234,56."""
    texto = f"{arredondar(valor):,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def interpretar_valor(texto: str) -> Decimal:
    """Converte '1.500,50', '1500,50' ou '1500.50' em Decimal."""
    limpo = texto.replace("R$", "").replace(" ", "").strip()
    if not limpo:
        raise ErroValidacao("Informe o valor do título.")

    if "," in limpo and "." in limpo:
        # O separador que aparece por último é o decimal.
        if limpo.rfind(",") > limpo.rfind("."):
            limpo = limpo.replace(".", "").replace(",", ".")
        else:
            limpo = limpo.replace(",", "")
    elif "," in limpo:
        limpo = limpo.replace(",", ".")
    elif limpo.count(".") > 1 or (limpo.count(".") == 1 and len(limpo.split(".")[1]) == 3):
        # '1.500' ou '1.234.567' -> separador de milhar (padrão brasileiro)
        limpo = limpo.replace(".", "")

    try:
        valor = Decimal(limpo)
    except InvalidOperation:
        raise ErroValidacao("Valor inválido. Exemplo: 1.500,00") from None
    if not valor.is_finite():
        raise ErroValidacao("Valor inválido. Exemplo: 1.500,00")
    return valor


def interpretar_data(texto: str) -> date:
    """Converte 'DD/MM/AAAA' em date."""
    try:
        return datetime.strptime(texto.strip(), "%d/%m/%Y").date()
    except ValueError:
        raise ErroValidacao("Data inválida. Use o formato DD/MM/AAAA.") from None


# ---------------------------- Comissões -----------------------------------
def calcular_comissao(valor: Decimal) -> Decimal:
    """Regra: < R$ 100 = 0% | R$ 100 a R$ 499,99 = 1% | >= R$ 500 = 5%."""
    if valor < LIMITE_SEM_COMISSAO:
        return Decimal("0")
    if valor < LIMITE_COMISSAO_BAIXA:
        return valor * TAXA_COMISSAO_BAIXA
    return valor * TAXA_COMISSAO_ALTA


@dataclass
class ResumoVendedor:
    vendedor: str
    quantidade: int = 0
    total_vendido: Decimal = Decimal("0")
    total_comissao: Decimal = Decimal("0")

    @property
    def comissao_efetiva(self) -> Decimal:
        """Percentual médio de comissão sobre o total vendido."""
        if self.total_vendido == 0:
            return Decimal("0")
        return self.total_comissao / self.total_vendido * 100


def consolidar_comissoes(vendas: Sequence[dict]) -> list[ResumoVendedor]:
    """Agrupa as vendas por vendedor e devolve o ranking por comissão (maior primeiro)."""
    resumos: dict[str, ResumoVendedor] = {}
    for venda in vendas:
        valor = Decimal(str(venda["valor"]))
        resumo = resumos.setdefault(venda["vendedor"], ResumoVendedor(venda["vendedor"]))
        resumo.quantidade += 1
        resumo.total_vendido += valor
        resumo.total_comissao += calcular_comissao(valor)
    return sorted(resumos.values(), key=lambda r: r.total_comissao, reverse=True)


# ------------------------------ Estoque -----------------------------------
@dataclass
class Produto:
    codigo: int
    descricao: str
    quantidade: int


@dataclass(frozen=True)
class Movimento:
    id_movimento: str
    momento: datetime
    codigo: int
    produto: str
    descricao: str
    tipo: str  # "E" (entrada) ou "S" (saída)
    quantidade: int
    saldo: int


class GerenciadorEstoque:
    """Controla saldo, valida movimentações e mantém o histórico da sessão."""

    def __init__(self, dados: dict) -> None:
        self._produtos = {
            item["codigoProduto"]: Produto(
                item["codigoProduto"], item["descricaoProduto"], int(item["estoque"])
            )
            for item in dados["estoque"]
        }
        self._movimentos: list[Movimento] = []
        self._ids_usados: set[str] = set()

    @property
    def produtos(self) -> list[Produto]:
        return sorted(self._produtos.values(), key=lambda p: p.codigo)

    @property
    def movimentos(self) -> list[Movimento]:
        return list(reversed(self._movimentos))  # mais recentes primeiro

    def registrar(
        self, id_movimento: str, codigo: int, descricao: str, quantidade: int, tipo: str
    ) -> Movimento:
        id_movimento = id_movimento.strip()
        descricao = descricao.strip()

        if not id_movimento or not descricao:
            raise ErroValidacao("Preencha todos os campos do formulário.")
        if id_movimento.upper() in self._ids_usados:
            raise ErroValidacao(f"O ID '{id_movimento}' já foi utilizado. Informe um ID único.")
        produto = self._produtos.get(codigo)
        if produto is None:
            raise ErroValidacao(f"Produto com código {codigo} não encontrado.")
        if quantidade <= 0:
            raise ErroValidacao("A quantidade deve ser maior que zero.")

        if tipo == "E":
            produto.quantidade += quantidade
        elif tipo == "S":
            if produto.quantidade < quantidade:
                raise ErroValidacao(
                    f"Estoque insuficiente: '{produto.descricao}' possui apenas "
                    f"{produto.quantidade} unidade(s)."
                )
            produto.quantidade -= quantidade
        else:
            raise ErroValidacao("Operação inválida.")

        movimento = Movimento(
            id_movimento, datetime.now(), produto.codigo, produto.descricao,
            descricao, tipo, quantidade, produto.quantidade,
        )
        self._movimentos.append(movimento)
        self._ids_usados.add(id_movimento.upper())
        return movimento


# ------------------------------- Juros ------------------------------------
@dataclass(frozen=True)
class ResultadoJuros:
    valor_original: Decimal
    vencimento: date
    consulta: date
    dias_atraso: int
    juros: Decimal
    total: Decimal


def calcular_juros(valor: Decimal, vencimento: date, hoje: date) -> ResultadoJuros:
    """Juros simples: valor x 2,5% x dias em atraso. Título em dia não tem juros."""
    dias = max((hoje - vencimento).days, 0)
    juros = valor * TAXA_JUROS_DIARIA * dias
    return ResultadoJuros(valor, vencimento, hoje, dias, juros, valor + juros)


# ==========================================================================
# INTERFACE
# ==========================================================================
import customtkinter as ctk  # noqa: E402

ctk.set_appearance_mode("System")  # acompanha o tema do sistema (claro/escuro)
ctk.set_default_color_theme("blue")

FAMILIA = "Segoe UI"

# Paleta (tuplas = (modo claro, modo escuro))
COR_PRIMARIA = "#2563EB"
COR_PRIMARIA_HOVER = "#1D4ED8"
COR_SUCESSO = "#16A34A"
COR_SUCESSO_HOVER = "#15803D"
COR_PERIGO = "#DC2626"
COR_ALERTA = "#D97706"
COR_SECUNDARIA = "#64748B"
COR_SECUNDARIA_HOVER = "#475569"
FUNDO_APP = ("#F1F5F9", "#0B1120")
FUNDO_CARD = ("#FFFFFF", "#1E293B")
FUNDO_SIDEBAR = "#0F172A"
BORDA = ("#E2E8F0", "#334155")
TEXTO = ("#0F172A", "#F1F5F9")
TEXTO_SUAVE = ("#64748B", "#94A3B8")
ZEBRA = ("#F8FAFC", "#243247")
CABECALHO_TABELA = ("#E2E8F0", "#334155")
BANNER_NEUTRO = ("#64748B", "#475569")


def fonte(tamanho: int = 13, peso: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=FAMILIA, size=tamanho, weight=peso)


@dataclass(frozen=True)
class Badge:
    """Célula de tabela exibida como uma etiqueta colorida."""
    texto: str
    cor: str


Celula = Union[str, tuple, Badge]


class Cartao(ctk.CTkFrame):
    """Painel branco/escuro com cantos arredondados e borda suave."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(
            master, fg_color=FUNDO_CARD, corner_radius=14,
            border_width=1, border_color=BORDA, **kwargs,
        )


class CartaoMetrica(Cartao):
    """Cartão de indicador: título pequeno + valor em destaque + barra colorida."""

    def __init__(self, master, titulo: str, cor: str = COR_PRIMARIA) -> None:
        super().__init__(master)
        ctk.CTkFrame(self, width=5, fg_color=cor, corner_radius=3).pack(
            side="left", fill="y", padx=(12, 0), pady=14
        )
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(side="left", fill="both", expand=True, padx=14, pady=12)
        ctk.CTkLabel(
            corpo, text=titulo.upper(), font=fonte(11, "bold"),
            text_color=TEXTO_SUAVE, anchor="w",
        ).pack(fill="x")
        self._valor = ctk.CTkLabel(corpo, text="—", font=fonte(22, "bold"),
                                   text_color=TEXTO, anchor="w")
        self._valor.pack(fill="x", pady=(2, 0))

    def definir(self, valor: str) -> None:
        self._valor.configure(text=valor)


class Tabela(ctk.CTkScrollableFrame):
    """Tabela com cabeçalho, linhas zebradas, badges e mensagem de lista vazia."""

    def __init__(self, master, colunas: Sequence[tuple[str, int, str]]) -> None:
        """colunas: sequência de (título, peso/largura relativa, alinhamento 'w'|'e'|'center')."""
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self._colunas = list(colunas)
        self._linhas: list[ctk.CTkBaseClass] = []

        cabecalho = self._nova_linha(CABECALHO_TABELA, linha=0, altura=34)
        for i, (titulo, _, ancora) in enumerate(self._colunas):
            ctk.CTkLabel(
                cabecalho, text=titulo.upper(), anchor=ancora,
                font=fonte(11, "bold"), text_color=TEXTO_SUAVE,
            ).grid(row=0, column=i, sticky="ew", padx=12, pady=6)

    def _nova_linha(self, fundo, linha: int, altura: int = 38) -> ctk.CTkFrame:
        quadro = ctk.CTkFrame(self, fg_color=fundo, corner_radius=8, height=altura)
        quadro.grid(row=linha, column=0, sticky="ew", pady=1)
        for i, (_, peso, _) in enumerate(self._colunas):
            quadro.grid_columnconfigure(i, weight=peso, uniform="c")
        return quadro

    def preencher(self, linhas: Sequence[Sequence[Celula]], vazio: str = "Sem dados.") -> None:
        for widget in self._linhas:
            widget.destroy()
        self._linhas.clear()

        if not linhas:
            aviso = ctk.CTkLabel(self, text=vazio, font=fonte(12), text_color=TEXTO_SUAVE)
            aviso.grid(row=1, column=0, pady=28)
            self._linhas.append(aviso)
            return

        for indice, valores in enumerate(linhas):
            fundo = ZEBRA if indice % 2 else "transparent"
            quadro = self._nova_linha(fundo, linha=indice + 1)
            self._linhas.append(quadro)
            for coluna, (valor, (_, _, ancora)) in enumerate(zip(valores, self._colunas)):
                self._criar_celula(quadro, coluna, valor, ancora)

    @staticmethod
    def _criar_celula(quadro, coluna: int, valor: Celula, ancora: str) -> None:
        if isinstance(valor, Badge):
            ctk.CTkLabel(
                quadro, text=valor.texto, fg_color=valor.cor, text_color="white",
                corner_radius=10, height=22, width=92, font=fonte(11, "bold"),
            ).grid(row=0, column=coluna, sticky="w", padx=12, pady=8)
            return
        texto, cor = valor if isinstance(valor, tuple) else (valor, None)
        ctk.CTkLabel(
            quadro, text=str(texto), anchor=ancora, font=fonte(12),
            text_color=cor or TEXTO,
        ).grid(row=0, column=coluna, sticky="ew", padx=12, pady=8)


class PaginaBase(ctk.CTkFrame):
    """Estrutura comum: cabeçalho (título + subtítulo) e área de conteúdo."""

    def __init__(self, master, titulo: str, subtitulo: str) -> None:
        super().__init__(master, fg_color="transparent")
        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.pack(fill="x", padx=28, pady=(24, 14))
        ctk.CTkLabel(cabecalho, text=titulo, font=fonte(26, "bold"),
                     text_color=TEXTO, anchor="w").pack(fill="x")
        ctk.CTkLabel(cabecalho, text=subtitulo, font=fonte(13),
                     text_color=TEXTO_SUAVE, anchor="w").pack(fill="x")
        self.corpo = ctk.CTkFrame(self, fg_color="transparent")
        self.corpo.pack(fill="both", expand=True, padx=28, pady=(0, 24))

    @staticmethod
    def _rotulo(master, texto: str) -> None:
        ctk.CTkLabel(master, text=texto, font=fonte(12, "bold"),
                     text_color=TEXTO, anchor="w").pack(fill="x", padx=20, pady=(10, 4))

    @staticmethod
    def _mostrar_feedback(rotulo: ctk.CTkLabel, mensagem: str, cor: str) -> None:
        rotulo.configure(text=mensagem, text_color=cor)


# --------------------------------------------------------------------------
# PÁGINA 1 - COMISSÕES
# --------------------------------------------------------------------------
class PaginaComissoes(PaginaBase):
    def __init__(self, master, vendas: Sequence[dict]) -> None:
        super().__init__(master, "Comissões da equipe",
                         "Consolidado de vendas e comissões por vendedor")
        self._vendas = vendas
        c = self.corpo
        c.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="metrica")
        c.grid_rowconfigure(1, weight=1)

        self.card_total = CartaoMetrica(c, "Total vendido", COR_PRIMARIA)
        self.card_comissao = CartaoMetrica(c, "Total de comissões", COR_SUCESSO)
        self.card_qtd = CartaoMetrica(c, "Vendas realizadas", COR_ALERTA)
        self.card_destaque = CartaoMetrica(c, "Maior comissão", "#7C3AED")
        for i, card in enumerate((self.card_total, self.card_comissao,
                                  self.card_qtd, self.card_destaque)):
            card.grid(row=0, column=i, sticky="ew", padx=(0, 12 if i < 3 else 0))

        cartao_tabela = Cartao(c)
        cartao_tabela.grid(row=1, column=0, columnspan=4, sticky="nsew", pady=(16, 12))
        topo = ctk.CTkFrame(cartao_tabela, fg_color="transparent")
        topo.pack(fill="x", padx=20, pady=(16, 6))
        ctk.CTkLabel(topo, text="Ranking de vendedores", font=fonte(16, "bold"),
                     text_color=TEXTO).pack(side="left")
        ctk.CTkButton(topo, text="Recalcular comissões", height=34, corner_radius=8,
                      font=fonte(12, "bold"), fg_color=COR_PRIMARIA,
                      hover_color=COR_PRIMARIA_HOVER,
                      command=self.calcular).pack(side="right")

        self.tabela = Tabela(cartao_tabela, [
            ("Pos.", 1, "w"), ("Vendedor", 5, "w"), ("Vendas", 2, "center"),
            ("Total vendido", 3, "e"), ("Comissão", 3, "e"), ("% efetivo", 2, "e"),
        ])
        self.tabela.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        regras = Cartao(c)
        regras.grid(row=2, column=0, columnspan=4, sticky="ew")
        ctk.CTkLabel(
            regras, font=fonte(12), text_color=TEXTO_SUAVE,
            text=("Regras de comissão    •    Abaixo de R$ 100,00: 0%    •    "
                  "De R$ 100,00 a R$ 499,99: 1%    •    A partir de R$ 500,00: 5%"),
        ).pack(padx=20, pady=12)

        self.calcular()

    def calcular(self) -> None:
        resumos = consolidar_comissoes(self._vendas)
        total_vendido = sum((r.total_vendido for r in resumos), Decimal("0"))
        total_comissao = sum((r.total_comissao for r in resumos), Decimal("0"))

        self.card_total.definir(formatar_brl(total_vendido))
        self.card_comissao.definir(formatar_brl(total_comissao))
        self.card_qtd.definir(str(sum(r.quantidade for r in resumos)))
        self.card_destaque.definir(resumos[0].vendedor if resumos else "—")

        linhas = [
            [f"{pos}º", r.vendedor, str(r.quantidade), formatar_brl(r.total_vendido),
             (formatar_brl(r.total_comissao), COR_SUCESSO),
             f"{arredondar(r.comissao_efetiva)}%".replace(".", ",")]
            for pos, r in enumerate(resumos, start=1)
        ]
        self.tabela.preencher(linhas, "Nenhuma venda encontrada.")


# --------------------------------------------------------------------------
# PÁGINA 2 - ESTOQUE
# --------------------------------------------------------------------------
class PaginaEstoque(PaginaBase):
    def __init__(self, master, estoque: GerenciadorEstoque) -> None:
        super().__init__(master, "Controle de estoque",
                         "Registre entradas e saídas e acompanhe o saldo em tempo real")
        self.estoque = estoque
        c = self.corpo
        c.grid_columnconfigure(0, weight=0, minsize=350)
        c.grid_columnconfigure(1, weight=1)
        c.grid_rowconfigure(0, weight=1)
        self._montar_formulario(c)
        self._montar_tabelas(c)
        self.atualizar()

    def _montar_formulario(self, c) -> None:
        form = Cartao(c)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        ctk.CTkLabel(form, text="Nova movimentação", font=fonte(16, "bold"),
                     text_color=TEXTO, anchor="w").pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(form, text="Todos os campos são obrigatórios.", font=fonte(12),
                     text_color=TEXTO_SUAVE, anchor="w").pack(fill="x", padx=20)

        self._rotulo(form, "ID único da movimentação")
        self.entry_id = ctk.CTkEntry(form, height=38, placeholder_text="Ex.: MOV-0001")
        self.entry_id.pack(fill="x", padx=20)

        self._rotulo(form, "Produto")
        valores = [f"{p.codigo} · {p.descricao}" for p in self.estoque.produtos]
        self.combo_produto = ctk.CTkComboBox(form, values=valores, height=38, state="readonly")
        self.combo_produto.set("Selecione um produto")
        self.combo_produto.pack(fill="x", padx=20)

        self._rotulo(form, "Descrição / motivo")
        self.entry_desc = ctk.CTkEntry(form, height=38, placeholder_text="Ex.: Venda, Reposição")
        self.entry_desc.pack(fill="x", padx=20)

        self._rotulo(form, "Quantidade")
        self.entry_qtd = ctk.CTkEntry(form, height=38, placeholder_text="Ex.: 10")
        self.entry_qtd.pack(fill="x", padx=20)

        self._rotulo(form, "Operação")
        self.seg_operacao = ctk.CTkSegmentedButton(form, values=["Entrada", "Saída"], height=36)
        self.seg_operacao.set("Entrada")
        self.seg_operacao.pack(fill="x", padx=20)

        botoes = ctk.CTkFrame(form, fg_color="transparent")
        botoes.pack(fill="x", padx=20, pady=(20, 8))
        ctk.CTkButton(botoes, text="Registrar", height=40, corner_radius=8,
                      font=fonte(13, "bold"), fg_color=COR_SUCESSO,
                      hover_color=COR_SUCESSO_HOVER,
                      command=self.registrar).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(botoes, text="Limpar", height=40, corner_radius=8,
                      font=fonte(13, "bold"), fg_color=COR_SECUNDARIA,
                      hover_color=COR_SECUNDARIA_HOVER,
                      command=self.limpar).pack(side="left", fill="x", expand=True, padx=(6, 0))

        self.feedback = ctk.CTkLabel(form, text="", font=fonte(12, "bold"), wraplength=300,
                                     justify="left", anchor="w")
        self.feedback.pack(fill="x", padx=20, pady=(4, 16))

    def _montar_tabelas(self, c) -> None:
        direita = ctk.CTkFrame(c, fg_color="transparent")
        direita.grid(row=0, column=1, sticky="nsew")
        direita.grid_columnconfigure(0, weight=1)
        direita.grid_rowconfigure((0, 1), weight=1, uniform="tabelas")

        saldo = Cartao(direita)
        saldo.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        ctk.CTkLabel(saldo, text="Saldo atual do depósito", font=fonte(16, "bold"),
                     text_color=TEXTO, anchor="w").pack(fill="x", padx=20, pady=(16, 6))
        self.tabela_estoque = Tabela(saldo, [
            ("Cód.", 1, "w"), ("Produto", 4, "w"), ("Qtd.", 1, "e"), ("Status", 2, "w"),
        ])
        self.tabela_estoque.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        historico = Cartao(direita)
        historico.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        ctk.CTkLabel(historico, text="Histórico da sessão", font=fonte(16, "bold"),
                     text_color=TEXTO, anchor="w").pack(fill="x", padx=20, pady=(16, 6))
        self.tabela_historico = Tabela(historico, [
            ("Hora", 2, "w"), ("ID", 2, "w"), ("Produto", 4, "w"),
            ("Tipo", 2, "w"), ("Qtd.", 1, "e"), ("Saldo", 1, "e"),
        ])
        self.tabela_historico.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # ----------------------------- ações ------------------------------------
    def _codigo_selecionado(self) -> int:
        try:
            return int(self.combo_produto.get().split("·")[0].strip())
        except ValueError:
            raise ErroValidacao("Selecione um produto.") from None

    def _quantidade_digitada(self) -> int:
        try:
            return int(self.entry_qtd.get().strip())
        except ValueError:
            raise ErroValidacao("A quantidade deve ser um número inteiro.") from None

    def registrar(self) -> None:
        try:
            tipo = "E" if self.seg_operacao.get() == "Entrada" else "S"
            movimento = self.estoque.registrar(
                self.entry_id.get(), self._codigo_selecionado(),
                self.entry_desc.get(), self._quantidade_digitada(), tipo,
            )
        except ValueError as erro:  # ErroValidacao herda de ValueError
            self._mostrar_feedback(self.feedback, f"✖ {erro}", COR_PERIGO)
            return

        acao = "Entrada" if movimento.tipo == "E" else "Saída"
        self._mostrar_feedback(
            self.feedback,
            f"✔ {acao} de {movimento.quantidade} un. registrada. "
            f"Novo saldo de '{movimento.produto}': {movimento.saldo}.",
            COR_SUCESSO,
        )
        self.atualizar()
        for entrada in (self.entry_id, self.entry_desc, self.entry_qtd):
            entrada.delete(0, "end")

    def limpar(self) -> None:
        for entrada in (self.entry_id, self.entry_desc, self.entry_qtd):
            entrada.delete(0, "end")
        self.combo_produto.set("Selecione um produto")
        self.seg_operacao.set("Entrada")
        self._mostrar_feedback(self.feedback, "", COR_SUCESSO)

    @staticmethod
    def _status(quantidade: int) -> Badge:
        if quantidade <= 0:
            return Badge("Sem estoque", COR_PERIGO)
        if quantidade < ESTOQUE_BAIXO:
            return Badge("Baixo", COR_ALERTA)
        return Badge("Normal", COR_SUCESSO)

    def atualizar(self) -> None:
        self.tabela_estoque.preencher([
            [str(p.codigo), p.descricao, str(p.quantidade), self._status(p.quantidade)]
            for p in self.estoque.produtos
        ])
        self.tabela_historico.preencher([
            [m.momento.strftime("%H:%M:%S"), m.id_movimento, m.produto,
             Badge("Entrada", COR_SUCESSO) if m.tipo == "E" else Badge("Saída", COR_PERIGO),
             str(m.quantidade), str(m.saldo)]
            for m in self.estoque.movimentos
        ], "Nenhuma movimentação registrada nesta sessão.")


# --------------------------------------------------------------------------
# PÁGINA 3 - JUROS
# --------------------------------------------------------------------------
def formatar_data_digitada(texto: str) -> str:
    """Aplica a máscara DD/MM/AAAA a qualquer sequência de dígitos."""
    digitos = "".join(c for c in texto if c.isdigit())[:8]
    partes = (digitos[:2], digitos[2:4], digitos[4:8])
    return "/".join(p for p in partes if p)


class PaginaJuros(PaginaBase):
    def __init__(self, master) -> None:
        super().__init__(master, "Juros por atraso",
                         "Juros simples de 2,5% ao dia sobre títulos vencidos")
        c = self.corpo
        c.grid_columnconfigure(0, weight=0, minsize=360)
        c.grid_columnconfigure(1, weight=1)
        c.grid_rowconfigure(0, weight=1)
        self._montar_formulario(c)
        self._montar_resultado(c)

    def _montar_formulario(self, c) -> None:
        form = Cartao(c)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        ctk.CTkLabel(form, text="Dados do título", font=fonte(16, "bold"),
                     text_color=TEXTO, anchor="w").pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(form, text="Informe o valor e a data de vencimento.", font=fonte(12),
                     text_color=TEXTO_SUAVE, anchor="w").pack(fill="x", padx=20)

        self._rotulo(form, "Valor original do título (R$)")
        self.entry_valor = ctk.CTkEntry(form, height=38, placeholder_text="Ex.: 1.500,00")
        self.entry_valor.pack(fill="x", padx=20)

        self._rotulo(form, "Data de vencimento")
        self.entry_venc = ctk.CTkEntry(form, height=38, placeholder_text="DD/MM/AAAA")
        self.entry_venc.pack(fill="x", padx=20)
        self.entry_venc.bind("<KeyRelease>", self._aplicar_mascara)

        for entrada in (self.entry_valor, self.entry_venc):
            entrada.bind("<Return>", lambda _e: self.calcular())

        botoes = ctk.CTkFrame(form, fg_color="transparent")
        botoes.pack(fill="x", padx=20, pady=(22, 8))
        ctk.CTkButton(botoes, text="Calcular", height=40, corner_radius=8,
                      font=fonte(13, "bold"), fg_color=COR_PRIMARIA,
                      hover_color=COR_PRIMARIA_HOVER,
                      command=self.calcular).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(botoes, text="Limpar", height=40, corner_radius=8,
                      font=fonte(13, "bold"), fg_color=COR_SECUNDARIA,
                      hover_color=COR_SECUNDARIA_HOVER,
                      command=self.limpar).pack(side="left", fill="x", expand=True, padx=(6, 0))

        self.feedback = ctk.CTkLabel(form, text="", font=fonte(12, "bold"), wraplength=310,
                                     justify="left", anchor="w")
        self.feedback.pack(fill="x", padx=20, pady=(4, 16))

    def _montar_resultado(self, c) -> None:
        direita = ctk.CTkFrame(c, fg_color="transparent")
        direita.grid(row=0, column=1, sticky="nsew")
        direita.grid_columnconfigure((0, 1), weight=1, uniform="r")

        self.banner = ctk.CTkLabel(
            direita, text="Aguardando os dados do título", fg_color=BANNER_NEUTRO,
            text_color="white", corner_radius=10, height=48, font=fonte(14, "bold"),
        )
        self.banner.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))

        self.card_original = CartaoMetrica(direita, "Valor original", COR_PRIMARIA)
        self.card_dias = CartaoMetrica(direita, "Dias em atraso", COR_ALERTA)
        self.card_juros = CartaoMetrica(direita, "Juros (2,5% ao dia)", COR_PERIGO)
        self.card_total = CartaoMetrica(direita, "Total atualizado", COR_SUCESSO)
        self.card_original.grid(row=1, column=0, sticky="ew", padx=(0, 7), pady=(0, 14))
        self.card_dias.grid(row=1, column=1, sticky="ew", padx=(7, 0), pady=(0, 14))
        self.card_juros.grid(row=2, column=0, sticky="ew", padx=(0, 7), pady=(0, 14))
        self.card_total.grid(row=2, column=1, sticky="ew", padx=(7, 0), pady=(0, 14))

        detalhes = Cartao(direita)
        detalhes.grid(row=3, column=0, columnspan=2, sticky="ew")
        self.lbl_detalhes = ctk.CTkLabel(
            detalhes, text="Os detalhes do cálculo aparecerão aqui.", font=fonte(12),
            text_color=TEXTO_SUAVE, justify="left", anchor="w",
        )
        self.lbl_detalhes.pack(fill="x", padx=20, pady=16)

    # ----------------------------- ações ------------------------------------
    def _aplicar_mascara(self, _evento=None) -> None:
        atual = self.entry_venc.get()
        formatado = formatar_data_digitada(atual)
        if formatado != atual:
            self.entry_venc.delete(0, "end")
            self.entry_venc.insert(0, formatado)

    def calcular(self) -> None:
        try:
            valor = interpretar_valor(self.entry_valor.get())
            if valor <= 0:
                raise ErroValidacao("O valor do título deve ser maior que zero.")
            vencimento = interpretar_data(self.entry_venc.get())
        except ValueError as erro:
            self._mostrar_feedback(self.feedback, f"✖ {erro}", COR_PERIGO)
            return

        self._mostrar_feedback(self.feedback, "", COR_SUCESSO)
        r = calcular_juros(valor, vencimento, date.today())

        self.card_original.definir(formatar_brl(r.valor_original))
        self.card_dias.definir(f"{r.dias_atraso} dia(s)")
        self.card_juros.definir(formatar_brl(r.juros))
        self.card_total.definir(formatar_brl(r.total))

        if r.dias_atraso == 0:
            self.banner.configure(text="✔  Título em dia ou a vencer — nenhum juro aplicado",
                                  fg_color=COR_SUCESSO)
        else:
            self.banner.configure(text=f"⚠  Título vencido há {r.dias_atraso} dia(s)",
                                  fg_color=COR_PERIGO)

        self.lbl_detalhes.configure(
            text=(f"Vencimento: {r.vencimento:%d/%m/%Y}\n"
                  f"Data da consulta: {r.consulta:%d/%m/%Y}\n"
                  f"Fórmula: juros = valor × 2,5% × dias em atraso"),
            text_color=TEXTO,
        )

    def limpar(self) -> None:
        self.entry_valor.delete(0, "end")
        self.entry_venc.delete(0, "end")
        self._mostrar_feedback(self.feedback, "", COR_SUCESSO)
        for card in (self.card_original, self.card_dias, self.card_juros, self.card_total):
            card.definir("—")
        self.banner.configure(text="Aguardando os dados do título", fg_color=BANNER_NEUTRO)
        self.lbl_detalhes.configure(text="Os detalhes do cálculo aparecerão aqui.",
                                    text_color=TEXTO_SUAVE)


# --------------------------------------------------------------------------
# JANELA PRINCIPAL
# --------------------------------------------------------------------------
class Aplicacao(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Sistema de Gestão — Desafio TI")
        self.geometry("1220x780")
        self.minsize(1100, 700)
        self.configure(fg_color=FUNDO_APP)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._botoes_menu: dict[str, ctk.CTkButton] = {}
        self._montar_menu_lateral()

        area = ctk.CTkFrame(self, fg_color="transparent")
        area.grid(row=0, column=1, sticky="nsew")
        area.grid_columnconfigure(0, weight=1)
        area.grid_rowconfigure(0, weight=1)

        self._paginas: dict[str, PaginaBase] = {
            "comissoes": PaginaComissoes(area, DADOS_VENDAS["vendas"]),
            "estoque": PaginaEstoque(area, GerenciadorEstoque(DADOS_ESTOQUE)),
            "juros": PaginaJuros(area),
        }
        for pagina in self._paginas.values():
            pagina.grid(row=0, column=0, sticky="nsew")
        self.mostrar("comissoes")

    def _montar_menu_lateral(self) -> None:
        menu = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=FUNDO_SIDEBAR)
        menu.grid(row=0, column=0, sticky="nsew")
        menu.pack_propagate(False)

        ctk.CTkLabel(menu, text="◆  GESTÃO TI", font=fonte(20, "bold"),
                     text_color="white", anchor="w").pack(fill="x", padx=24, pady=(32, 0))
        ctk.CTkLabel(menu, text="Painel do desafio", font=fonte(12),
                     text_color="#94A3B8", anchor="w").pack(fill="x", padx=24, pady=(0, 28))

        itens = (("comissoes", "💰   Comissões"), ("estoque", "📦   Estoque"),
                 ("juros", "🧮   Juros"))
        for chave, texto in itens:
            botao = ctk.CTkButton(
                menu, text=texto, anchor="w", height=44, corner_radius=10,
                font=fonte(14, "bold"), fg_color="transparent", text_color="#CBD5E1",
                hover_color="#1E293B", command=lambda k=chave: self.mostrar(k),
            )
            botao.pack(fill="x", padx=14, pady=3)
            self._botoes_menu[chave] = botao

        rodape = ctk.CTkFrame(menu, fg_color="transparent")
        rodape.pack(side="bottom", fill="x", padx=14, pady=20)
        ctk.CTkLabel(rodape, text="Aparência", font=fonte(11, "bold"),
                     text_color="#94A3B8", anchor="w").pack(fill="x", padx=4, pady=(0, 6))
        self._mapa_tema = {"Auto": "System", "Claro": "Light", "Escuro": "Dark"}
        seletor = ctk.CTkSegmentedButton(
            rodape, values=list(self._mapa_tema), command=self._trocar_tema,
            fg_color="#1E293B", unselected_color="#1E293B", selected_color=COR_PRIMARIA,
            selected_hover_color=COR_PRIMARIA_HOVER, unselected_hover_color="#334155",
            text_color="#E2E8F0", font=fonte(11, "bold"),
        )
        seletor.set("Auto")
        seletor.pack(fill="x")

    def _trocar_tema(self, escolha: str) -> None:
        ctk.set_appearance_mode(self._mapa_tema[escolha])

    def mostrar(self, chave: str) -> None:
        self._paginas[chave].tkraise()
        for nome, botao in self._botoes_menu.items():
            ativo = nome == chave
            botao.configure(fg_color=COR_PRIMARIA if ativo else "transparent",
                            text_color="white" if ativo else "#CBD5E1")


if __name__ == "__main__":
    Aplicacao().mainloop()
