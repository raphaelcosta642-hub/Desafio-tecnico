# Desafio-tecnico
# Sistema de Gestão — Desafio TI

Aplicação desktop em **Python + CustomTkinter** com três módulos:

| Módulo | O que faz |
|---|---|
| **Comissões** | Consolida vendas por vendedor. Regra: `< R$ 100` = 0% · `R$ 100 a 499,99` = 1% · `≥ R$ 500` = 5%. |
| **Estoque** | Registra entradas e saídas, impede saldo negativo, exige ID único e mantém histórico da sessão. |
| **Juros** | Juros simples de 2,5% ao dia sobre títulos vencidos, com máscara automática de data. |

## Como executar

```bash
pip install -r requirements.txt
python sistema_desafio_ti.py
```

## Destaques técnicos

- Regras de negócio **separadas da interface** (funções e classes sem dependência da tela).
- Valores monetários com `Decimal`, sem erros de ponto flutuante, e formatação em R$.
- Validações com mensagens claras: ID duplicado, quantidade inválida, estoque insuficiente e data inválida.
- Interface com menu lateral, cartões de indicadores, tabelas e tema claro/escuro.

## Próximos passos

- Salvar os dados em um banco de dados (hoje ficam apenas em memória).
- Criar testes automatizados para as regras de negócio.
- Adicionar login e controle de usuários.

## Autor

Thalles Raphael Moreira da Costa
