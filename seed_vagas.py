r"""Script único: limpa as vagas atuais e popula com TODAS as vagas reais da
Contato Facilities (a partir do material recebido em VAGAS 2026 + POST DE VAGAS).

Para rodar com encoding correto no Windows:

    $env:PYTHONIOENCODING="utf-8"
    .\.venv\Scripts\python.exe seed_vagas.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

# URL do portal. Use a variável de ambiente SEED_BASE_URL ou passe a URL como
# primeiro argumento para apontar para produção. Ex.:
#   python seed_vagas.py https://seu-app.vercel.app
BASE = (
    (sys.argv[1] if len(sys.argv) > 1 else None)
    or os.environ.get("SEED_BASE_URL")
    or "http://127.0.0.1:5000"
).rstrip("/")


def request(method: str, path: str, data: dict | None = None) -> dict | list:
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


VAGAS: list[dict[str, str]] = [
    # ============================================================
    # ADMINISTRATIVO / ANÁLISE / ESCRITÓRIO
    # ============================================================
    {
        "titulo": "Analista Administrativo",
        "descricao": (
            "Manaus/AM (Dom Pedro). Atuar em rotinas administrativas, processos "
            "licitatórios, recapctuação e cadastro nos portais de renovação documental. "
            "Apoiar a área comercial e jurídica na elaboração e gestão de contratos."
        ),
        "requisitos": (
            "Formação superior em Administração, Direito, Contabilidade ou áreas "
            "correlatas. Conhecimento básico em CLT e Licitação. Boa escrita. "
            "Conhecimento no processo licitatório: recapctuação e cadastro nos portais "
            "de renovação documental. Organização e pontualidade. Conhecimento no "
            "sistema TOTVS/PROTHEUS será um diferencial. Vagas abertas inclusive PCD."
        ),
    },
    {
        "titulo": "Assistente Administrativo",
        "descricao": (
            "Manaus/AM. Apoiar rotinas administrativas: arquivo, atendimento, emissão "
            "de relatórios e suporte aos demais setores. Pacote Office (Word, Excel, "
            "Outlook). Noções de sistemas ERP e gestão empresarial."
        ),
        "requisitos": (
            "Ensino Médio completo (desejável Técnico ou Superior em Administração, "
            "Contabilidade ou áreas afins). Experiência em rotinas administrativas. "
            "Organização, boa comunicação verbal e escrita, agilidade, sigilo e atenção "
            "aos prazos. Diferencial: lançamentos em sistema."
        ),
    },
    {
        "titulo": "Analista de Compras",
        "descricao": (
            "Manaus/AM (Dom Pedro). Realizar cotações e negociações com fornecedores, "
            "emitir pedidos de compras no sistema TOTVS/Protheus, acompanhar pedidos "
            "até a entrega final, controlar contratos e prazos, análise de mercado, "
            "gestão de orçamento, cadastro de material/serviço."
        ),
        "requisitos": (
            "Ensino superior completo ou cursando em Administração, Contabilidade ou "
            "áreas correlatas. Experiência prévia em rotinas de compras. Vivência com "
            "TOTVS/Protheus (diferencial). Boa comunicação, senso de urgência, "
            "habilidade de negociação. Análise de custos e noção tributária. PCD."
        ),
    },
    {
        "titulo": "Assistente de Compras",
        "descricao": (
            "Manaus/AM (Dom Pedro). Apoiar a equipe de compras em cotações, pregões "
            "eletrônicos e presenciais, e demais rotinas de suprimentos."
        ),
        "requisitos": (
            "Cursando ou com formação em Administração, Contabilidade, Logística ou "
            "áreas correlatas. Conhecimento da Lei de Licitações (14.133/2021). "
            "Experiência com pregões eletrônicos e presenciais. PCD."
        ),
    },
    {
        "titulo": "Analista de Licitação",
        "descricao": (
            "Manaus/AM (Dom Pedro). Atuar em processos licitatórios, pregões eletrônicos "
            "e presenciais, leitura e interpretação de editais, habilitação documental."
        ),
        "requisitos": (
            "Formação superior em Administração, Direito, Contabilidade ou áreas "
            "correlatas. Conhecimento da Lei de Licitações 14.133/2021 e demais "
            "legislações aplicáveis. Experiência com pregões eletrônicos e presenciais. "
            "Boa escrita e leitura. Conhecimentos técnicos em processos licitatórios. "
            "Conhecimento dos documentos necessários para habilitação. TOTVS/PROTHEUS "
            "diferencial. PCD."
        ),
    },
    {
        "titulo": "Analista de Logística",
        "descricao": (
            "Manaus/AM (Dom Pedro). Atuar no planejamento logístico, rotina de "
            "transporte, armazenagem, controle de estoque e distribuição. Análise de "
            "KPIs logísticos e indicadores de desempenho."
        ),
        "requisitos": (
            "Ensino superior completo em Logística, Administração ou áreas correlatas. "
            "Experiência prévia em logística, cadeia de suprimentos ou planejamento. "
            "Domínio do Excel (fórmulas, tabelas dinâmicas, gráficos, dashboards). "
            "Conhecimento em sistema de gestão. Entendimento de KPIs logísticos. "
            "Capacidade de lidar com situações de emergência. Metodologia de melhoria "
            "contínua. PCD."
        ),
    },
    {
        "titulo": "Analista de RH (Foco Admissão)",
        "descricao": (
            "Manaus/AM (Dom Pedro). Realizar o processo admissional de ponta a ponta: "
            "conferência de documentação, agilidade na contratação, recrutamento e "
            "seleção. Elaborar e acompanhar contratos de trabalho, termos e "
            "formulários relacionados à admissão. Realizar pré-onboarding e dar "
            "suporte à integração de novos colaboradores. Atualizar controles e "
            "relatórios da área admissional. Garantir que todas as etapas do processo "
            "admissional estejam devidamente registradas em sistema."
        ),
        "requisitos": (
            "Formação superior completa em Psicologia, Administração, Recursos "
            "Humanos ou áreas correlatas. Boa comunicação, organização, atenção a "
            "detalhes e foco em resultados. Familiaridade com sistemas RM, TOTVS "
            "Protheus e plataformas de vagas. PCD."
        ),
    },
    {
        "titulo": "Analista Financeiro",
        "descricao": (
            "Manaus/AM (Dom Pedro). Atuar de forma estratégica e analítica na área "
            "financeira utilizando o sistema Protheus. Gerir rotinas financeiras, "
            "realizar análise de custos, fluxo de caixa, conciliações e garantir a "
            "eficiência dos processos contábeis e financeiros."
        ),
        "requisitos": (
            "Formação superior em Administração, Contabilidade, Economia ou áreas "
            "correlatas. Experiência comprovada na área financeira, com ênfase em "
            "rotinas de fluxo de caixa, contas a pagar e a receber, conciliação "
            "bancária e relatórios financeiros. Conhecimento avançado do Protheus "
            "(principalmente módulo financeiro). Domínio de Excel avançado para "
            "análise e elaboração de relatórios financeiros. Visão analítica e "
            "habilidade para interpretação de demonstrações financeiras e indicadores "
            "de performance. Organização, atenção aos detalhes e habilidade para "
            "trabalhar com prazos e metas."
        ),
    },
    {
        "titulo": "Assistente Financeiro",
        "descricao": (
            "Manaus/AM (Dom Pedro). Realizar rotinas do setor financeiro e "
            "administrativo em geral. Executar com atenção todas as tarefas, garantir "
            "fluidez dos processos e dos setores correlatos. Auxiliar a disseminar a "
            "cultura da empresa para integração dos colaboradores."
        ),
        "requisitos": (
            "Formado em Administração, Economia, Ciências Contábeis ou áreas "
            "correlatas. Conhecimento no Pacote Office (Word, Excel, Power Point). "
            "Conhecer sistemas TOTVS. Conhecer rotinas de contas a pagar/receber. "
            "Conhecer rotinas de faturamento."
        ),
    },
    {
        "titulo": "Auxiliar Financeiro",
        "descricao": (
            "Manaus/AM (Dom Pedro). Apoiar as rotinas financeiras: contas a pagar e "
            "receber, conciliações e faturamento. Realizar visitas técnicas às "
            "unidades, quando necessário."
        ),
        "requisitos": (
            "Cursando Ensino Superior em Administração, Economia, Ciências Econômicas "
            "ou áreas correlatas. Conhecimentos no Pacote Office (Word, Excel e Power "
            "Point). Conhecer sistemas TOTVS. Conhecer rotinas de contas a pagar / "
            "receber. Conhecer rotinas de faturamento."
        ),
    },
    {
        "titulo": "Coordenador de Contratos",
        "descricao": (
            "Manaus/AM (Dom Pedro). Liderança da gestão e execução de contratos "
            "administrativos, com foco em terceirização (limpeza, conservação, apoio "
            "técnico-operacional). Domínio do sistema TOTVS Protheus (módulos "
            "Contratos, Faturamento) com parametrizações e análise sistêmica."
        ),
        "requisitos": (
            "Formação superior completa em Direito, Gestão Pública ou áreas correlatas. "
            "Pós-graduação em Gestão de Contratos, Direito Administrativo, "
            "Controladoria ou Compliance é diferencial. Experiência comprovada em "
            "gestão e execução de contratos administrativos. Conhecimento avançado em "
            "Excel, Power BI e ferramentas de análise. Vivência em repactuação e "
            "reequilíbrio econômico-financeiro, IPCA/INPC/IGPM e convenções coletivas. "
            "Sólida compreensão das Leis 14.133/2021, 8.666/1993 e Decreto 11.246/2022."
        ),
    },
    {
        "titulo": "Supervisor de Qualidade",
        "descricao": (
            "Manaus/AM (Dom Pedro). Supervisionar a equipe de qualidade nas rotinas "
            "de inspeção, auditoria e controle de processos. Aplicar e revisar normas "
            "e padrões de qualidade, treinar colaboradores em políticas e práticas, "
            "assegurar conformidade com requisitos legais, ambientais, de segurança "
            "e de clientes. Implantação e manutenção de certificações (ISO, OHSAS)."
        ),
        "requisitos": (
            "Ensino superior completo em Engenharia, Administração, Gestão da "
            "Qualidade ou áreas afins. Experiência em supervisão/coordenação. "
            "Ferramentas de qualidade (PDCA, 5S, Kaizen, MASP, Ishikawa). Vivência "
            "com auditorias internas e externas. Domínio de normas ISO 9001. "
            "Liderança, comunicação assertiva e visão estratégica. Sistema TOTVS "
            "Protheus."
        ),
    },

    # ============================================================
    # SAÚDE / OCUPACIONAL / SESMT
    # ============================================================
    {
        "titulo": "Analista de SESMT",
        "descricao": (
            "Manaus/AM (Dom Pedro). Elaborar, implementar e acompanhar programas "
            "legais como PGR, PCMSO, LTCAT, PPP, ASO. Atuar na investigação e análise "
            "de acidentes de trabalho propondo ações corretivas e preventivas. "
            "Monitorar cumprimento das NRs. Controlar entrega e validade de EPIs e "
            "EPCs. Acompanhar exames ocupacionais e afastamentos."
        ),
        "requisitos": (
            "Perfil de liderança. Certificações adicionais em Ergonomia, NR-33, "
            "NR-35, NR-10, Higiene Ocupacional. Conhecimento em equipamentos de "
            "medições ambientais. Sistema SOC, RM e TOTVS. CNH B. PCD."
        ),
    },
    {
        "titulo": "Auxiliar de SESMT",
        "descricao": (
            "Manaus/AM (Dom Pedro). Realizar gestão de controle e entrega de EPIs. "
            "Agendamento de exames ocupacionais e controle do PCMSO. Apoiar o "
            "gerenciamento de afastados previdenciários. Acompanhar/realizar "
            "treinamentos de segurança. Registrar ocorrências e auxiliar na "
            "investigação de acidentes de trabalho. Realizar visitas técnicas às "
            "unidades. Proatividade e trabalho em equipe."
        ),
        "requisitos": (
            "Boa comunicação. Pacote Office (planilhas, e-mail, sistemas de controle). "
            "Conhecimento básico de informática. Equipamentos de medições ambientais. "
            "Conhecimento no sistema RM e SOC. PCD."
        ),
    },
    {
        "titulo": "TST (Técnico de Segurança do Trabalho)",
        "descricao": (
            "Manaus/AM (Dom Pedro). Elaborar, implementar e acompanhar programas "
            "legais (PGR, PCMSO, LTCAT, PPP, ASO). Atuar na investigação e análise "
            "de acidentes. Monitorar NRs (NR-01, NR-09, NR-10, NR-17, NR-33, NR-35, "
            "NR-32). Controlar EPIs/EPCs. Coordenar campanhas de segurança (SIPAT, "
            "CIPA, DDS, treinamentos). Acompanhar exames ocupacionais e afastamentos. "
            "Realizar auditorias internas e apoiar inspeções externas (Ministério do "
            "Trabalho, perícias, seguradoras). Visitas técnicas."
        ),
        "requisitos": (
            "Curso Técnico em Segurança do Trabalho. Certificações em Ergonomia, "
            "NR-33, NR-35, NR-10 e Higiene Ocupacional são diferenciais. Conhecimento "
            "em equipamentos de medições ambientais. Sistemas SOC, RM e TOTVS. CNH B. PCD."
        ),
    },
    {
        "titulo": "Psicólogo (PJ) — Saúde Ocupacional",
        "descricao": (
            "Manaus/AM (Dom Pedro). Carga horária 12h semanais (4h/dia — segundas, "
            "quartas e sextas) das 08h às 12h. Local: presencial na sede "
            "administrativa, com possibilidade de atendimento remoto para outras "
            "unidades. Regime PJ. Atuar na identificação, prevenção e mitigação de "
            "riscos psicossociais no ambiente de trabalho. Atendimentos individuais "
            "e coletivos voltados ao bem-estar emocional e saúde mental. Elaborar e "
            "atualizar documentos relacionados à gestão de riscos psicossociais (GRO). "
            "Propor ações preventivas. Modalidade remota para unidades externas."
        ),
        "requisitos": (
            "Formação superior completa em Psicologia, com registro ativo no CRP. "
            "Experiência prévia em saúde ocupacional e/ou programas de saúde mental "
            "no trabalho. Conhecimento das diretrizes da NR-01, GRO e riscos "
            "psicossociais. Habilidade para atendimento clínico breve e orientação "
            "de casos com foco ocupacional. Boa comunicação, ética profissional e "
            "postura colaborativa."
        ),
    },
    {
        "titulo": "Artífice de Serviços Gerais",
        "descricao": (
            "Manaus/AM (Dom Pedro). Limpeza diária de chão, paredes, corrimões, "
            "escadas, bancadas e bebedouros utilizando ferramentas adequadas. Fazer "
            "registro das áreas higienizadas conforme protocolo. Comunicar ao "
            "encarregado sobre deteriorações (vasos sanitários, descargas, pias, "
            "cestos de lixo) ou avarias encontradas. Auxiliar o encarregado na lista "
            "de compras de produtos necessários. Estar em contato com a equipe e "
            "prestar auxílio quando necessário."
        ),
        "requisitos": (
            "Ensino Médio completo. Experiência mínima de 1 ano na área. "
            "Conhecimento em produtos de limpeza e funções. Disponibilidade de horário."
        ),
    },

    # ============================================================
    # OPERACIONAL — SERVIÇOS GERAIS / PORTARIA / JARDIM
    # ============================================================
    {
        "titulo": "Auxiliar de Serviços Gerais (ASG)",
        "descricao": (
            "Realizar a limpeza e conservação de ambientes internos e externos "
            "(salas, banheiros, corredores, áreas comuns, pátios). Executar coleta e "
            "descarte adequado de resíduos. Repor materiais de higiene. Zelar pela "
            "organização e conservação. Apoiar em organização de ambientes para "
            "reuniões e eventos. Cumprir normas de segurança, saúde e meio ambiente."
        ),
        "requisitos": (
            "Ensino fundamental completo (Médio é diferencial). Experiência anterior "
            "é diferencial. Conhecimento básico de produtos de limpeza. Noções de "
            "higiene, organização e conservação."
        ),
    },
    {
        "titulo": "ASG — Hospitalar (Manaus)",
        "descricao": (
            "Manaus/AM. Realizar atividades de limpeza, conservação e organização de "
            "ambientes internos e externos em ambiente hospitalar, garantindo "
            "trabalho seguro, limpo e agradável. Respeitar normas de higiene e "
            "segurança da empresa."
        ),
        "requisitos": (
            "Ensino fundamental ou médio completo. Sexo Masculino (exigência do "
            "posto). Boa comunicação e trabalho em equipe. Proatividade e organização. "
            "Experiência na área hospitalar é diferencial."
        ),
    },
    {
        "titulo": "ASG — Exclusiva para PCD (Manaus)",
        "descricao": (
            "Manaus/AM. Vaga EXCLUSIVA para Pessoa com Deficiência (PCD). Realizar "
            "atividades de limpeza, conservação e organização de ambientes internos e "
            "externos em ambiente seguro e agradável. Jornada de 8h diárias. "
            "Salário R$ 1.550,00. Benefícios: VT, VR, Cesta Básica, Plano de Saúde "
            "100% custeado pela empresa, Plano Odontológico, Seguro de Vida, "
            "premiações por desempenho e assiduidade."
        ),
        "requisitos": (
            "Ensino fundamental ou médio completo. Laudo médico atualizado "
            "comprovando a deficiência. Capacidade de realizar tarefas físicas leves "
            "a moderadas. Boa comunicação e trabalho em equipe. Proatividade e "
            "organização. Experiência na função é diferencial."
        ),
    },
    {
        "titulo": "ASG Intermitente (Masculino) — Manaus",
        "descricao": (
            "Manaus/AM (Zona Sul). Contrato intermitente. Realizar atividades de "
            "limpeza e conservação. Organização de ambientes internos e externos. "
            "Garantir ambiente de trabalho seguro, limpo e agradável."
        ),
        "requisitos": (
            "Ensino fundamental ou médio completo. Boa comunicação e trabalho em "
            "equipe. Proatividade e organização. Experiência na função é diferencial. "
            "Ser do gênero masculino (exigência do posto)."
        ),
    },
    {
        "titulo": "ASG Intermitente (Masculino) — TRE Paraíba",
        "descricao": (
            "João Pessoa/PB — posto TRE-PB. Contrato intermitente. Realizar "
            "atividades de limpeza e conservação. Organização de ambientes internos "
            "e externos. Garantir ambiente seguro, limpo e agradável."
        ),
        "requisitos": (
            "Ensino fundamental ou médio completo. Boa comunicação e trabalho em "
            "equipe. Proatividade e organização. Experiência é diferencial. Ser do "
            "gênero masculino (exigência do posto)."
        ),
    },
    {
        "titulo": "Jardineiro — Intermitente (RS)",
        "descricao": (
            "IFFAR Campus Frederico Westphalen/RS. Contrato intermitente. Realizar "
            "conservação, manutenção e embelezamento de áreas externas, garantindo "
            "ambientes agradáveis e bem cuidados."
        ),
        "requisitos": (
            "Desejável ensino fundamental completo. Experiência comprovada em "
            "jardinagem. Conhecimento em manutenção de áreas verdes (poda, adubação, "
            "capina, controle de pragas). Habilidade no manuseio de ferramentas e "
            "equipamentos de jardinagem (roçadeira, tesoura de poda, cortador de "
            "grama). Capacidade de manter a organização e limpeza dos espaços verdes."
        ),
    },
    {
        "titulo": "Agente de Portaria",
        "descricao": (
            "Manaus/AM (Dom Pedro). Controlar o acesso de pessoas e veículos. "
            "Realizar identificação e registro de visitantes, fornecedores e "
            "prestadores. Atender e direcionar chamados. Receber, conferir e "
            "encaminhar correspondências. Manter organização e limpeza da portaria. "
            "Auxiliar na evacuação de emergência. Prestar atendimento ao público "
            "com cordialidade. Realizar rondas periódicas."
        ),
        "requisitos": (
            "Ensino Médio completo. Experiência na função. Conhecimento básico em "
            "informática. Disponibilidade para turnos. Capacidade de lidar com "
            "emergências. Boa comunicação verbal e escrita. Curso de formação de "
            "vigilantes."
        ),
    },
    {
        "titulo": "Agente de Portaria / Porteiro — Manaus",
        "descricao": (
            "Manaus/AM. Noções básicas de segurança patrimonial. Registro de "
            "entrada e saída de pessoas e veículos. Controle de acessos e normas "
            "internas. Desejável experiência em portaria, recepção ou atendimento."
        ),
        "requisitos": (
            "Ensino Fundamental completo. Curso Agente de Portaria. Atenção, "
            "disciplina, cordialidade e postura profissional. Diferencial: "
            "informática básica (interfone, sistemas, controle de entrada/saída) e "
            "capacidade de lidar com público. Benefícios: VT, VR, Cesta Básica, "
            "Seguro de Vida, Plano Odontológico."
        ),
    },
    {
        "titulo": "Porteiro — Exclusiva para PCD",
        "descricao": (
            "Manaus/AM. Vaga EXCLUSIVA para PCD. Controlar acesso de pessoas e "
            "veículos, atendimento ao público interno e externo, registro de visitantes "
            "e zelo pela segurança patrimonial."
        ),
        "requisitos": (
            "Ensino Fundamental completo. Laudo médico atualizado. Boa comunicação. "
            "Atenção e disciplina. Curso de formação de Agente de Portaria é "
            "diferencial."
        ),
    },
    {
        "titulo": "Agente de Portaria — Intermitente (IFAM Tefé)",
        "descricao": (
            "Tefé/AM — IFAM Tefé. Contrato intermitente. Atuar como Agente de "
            "Portaria responsável pela segurança e organização do ambiente, "
            "atendimento ao público, controle de acessos e monitoramento de áreas "
            "comuns."
        ),
        "requisitos": (
            "Ensino médio completo. Curso de AGP. Experiência prévia em portaria ou "
            "áreas relacionadas é diferencial. Conhecimento básico de informática. "
            "Boa comunicação verbal e escrita. Disponibilidade de horário. "
            "Proatividade, responsabilidade e compromisso com a segurança."
        ),
    },
    {
        "titulo": "Encarregado — Portaria",
        "descricao": (
            "Encarregado responsável pela liderança da equipe de portaria, "
            "garantindo cumprimento de procedimentos, controle de acessos e "
            "atendimento de qualidade."
        ),
        "requisitos": (
            "Ensino Médio completo. Experiência em liderança de equipes de portaria. "
            "Boa comunicação, disciplina e organização."
        ),
    },

    # ============================================================
    # ESTOQUE / ALMOXARIFADO
    # ============================================================
    {
        "titulo": "Almoxarife",
        "descricao": (
            "Manaus/AM. Experiência comprovada em almoxarifado. Gestão de estoque e "
            "inventário. Controle de entradas e saídas de materiais. Emissão e "
            "conferência de notas fiscais. Domínio de sistemas informatizados de "
            "gestão de estoque. Organização, liderança, atenção aos detalhes, "
            "responsabilidade e iniciativa. Benefícios: VT, VR, Cesta Básica, Seguro "
            "de Vida, Plano Odontológico."
        ),
        "requisitos": (
            "Ensino Médio completo. Experiência comprovada em almoxarifado. PCD."
        ),
    },
    {
        "titulo": "Auxiliar de Almoxarifado",
        "descricao": (
            "Manaus/AM. Apoiar o controle, organização e movimentação de materiais "
            "no almoxarifado. Recebimento, conferência, armazenamento e distribuição "
            "de materiais. Controle de notas fiscais e pedidos. Noções de informática "
            "(sistemas de estoque/ERP). Organização, agilidade, atenção aos detalhes "
            "e trabalho em equipe."
        ),
        "requisitos": (
            "Ensino Médio completo. Desejável experiência em rotinas de estoque e "
            "almoxarifado. Cursando ou curso de logística. Noções de organização e "
            "controle de inventário. Benefícios: VT, VR, Cesta Básica, Seguro de "
            "Vida, Plano Odontológico."
        ),
    },
    {
        "titulo": "Auxiliar de Almoxarifado — IFAM Tefé",
        "descricao": (
            "Tefé/AM — IFAM Tefé. Atuar no controle, organização e movimentação de "
            "materiais e produtos no almoxarifado, garantindo eficiência, organização "
            "e segurança."
        ),
        "requisitos": (
            "Ensino Médio completo (desejável Ensino Técnico em Logística ou áreas "
            "correlatas). Experiência anterior em almoxarifado ou em funções "
            "similares. Conhecimento em controle de estoque e inventário. "
            "Habilidade no uso de sistemas de gestão de almoxarifado (desejável). "
            "Noções de segurança e boas práticas no ambiente de trabalho. "
            "Boa comunicação e capacidade de trabalhar em equipe. Proatividade, "
            "organização e atenção aos detalhes."
        ),
    },
    {
        "titulo": "Auxiliar de Almoxarifado — Intermitente (Tefé)",
        "descricao": (
            "Tefé/AM — IFAM Tefé. Contrato intermitente. Atuar no controle, "
            "organização e movimentação de materiais no almoxarifado em regime "
            "intermitente."
        ),
        "requisitos": (
            "Ensino Médio completo (desejável Ensino Técnico em Logística). "
            "Experiência em almoxarifado ou funções similares. Conhecimento em "
            "controle de estoque. Boa comunicação e trabalho em equipe."
        ),
    },
    {
        "titulo": "Auxiliar de Estoque",
        "descricao": (
            "Atuar no controle, organização e movimentação de materiais. Recebimento, "
            "armazenamento e expedição de mercadorias com eficiência e segurança. "
            "Receber, conferir e armazenar produtos. Realizar a separação e "
            "organização. Apoiar controle de entradas e saídas. Auxiliar em "
            "inventários periódicos. Apoiar carga e descarga."
        ),
        "requisitos": (
            "Ensino médio completo. Experiência prévia é diferencial. Organização, "
            "atenção aos detalhes e proatividade."
        ),
    },
    {
        "titulo": "Auxiliar de Estoque — Carga e Descarga",
        "descricao": (
            "Manaus/AM. Função com foco em carga e descarga: atividades físicas, "
            "movimentação de mercadorias, apoio à logística do depósito."
        ),
        "requisitos": (
            "Ensino médio completo. Experiência anterior em atividades de carga e "
            "descarga (desejável). Boa disposição física e capacidade para realizar "
            "atividades pesadas. Facilidade para trabalhar em equipe. "
            "Comprometimento e responsabilidade. PCD."
        ),
    },

    # ============================================================
    # ESTÁGIOS
    # ============================================================
    {
        "titulo": "Estagiário Administrativo",
        "descricao": (
            "Manaus/AM (Dom Pedro). Apoiar no controle e organização de documentos e "
            "relatórios administrativos. Auxiliar no lançamento e atualização de "
            "informações em sistemas internos. Acompanhar indicadores e auxiliar na "
            "elaboração de planilhas e controles. Contribuir para a melhoria dos "
            "processos internos. Apoiar a área em rotinas administrativas e "
            "atendimento aos colaboradores."
        ),
        "requisitos": (
            "Estar cursando Administração, Logística ou áreas correlatas (a partir "
            "do 4º período). Conhecimentos em Pacote Office (principalmente Excel e "
            "Word). Boa comunicação verbal e escrita, organização, proatividade e "
            "senso de urgência. PCD."
        ),
    },
    {
        "titulo": "Estagiário ADM — Operações",
        "descricao": (
            "Manaus/AM (Dom Pedro). Vaga de estágio focada em apoio a operações "
            "administrativas: documentos, relatórios, lançamentos em sistema, "
            "acompanhamento de indicadores e atendimento aos colaboradores."
        ),
        "requisitos": (
            "Estar cursando Administração, Logística ou áreas correlatas (a partir "
            "do 4º período). Conhecimentos em Pacote Office (principalmente Excel e "
            "Word). Boa comunicação, organização e proatividade. PCD."
        ),
    },
    {
        "titulo": "Estagiário de DP/RH",
        "descricao": (
            "Manaus/AM (Dom Pedro). Apoiar no processo de admissão de novos "
            "colaboradores (coleta e conferência de documentação, integração, "
            "atualização de cadastros). Auxiliar no controle de ponto eletrônico, "
            "banco de horas e férias. Organização e arquivamento de documentos. "
            "Apoiar a área em rotinas administrativas e no atendimento aos "
            "colaboradores."
        ),
        "requisitos": (
            "Cursando Ensino Superior em Administração, Recursos Humanos, Psicologia "
            "ou áreas correlatas. Pacote Office (principalmente Excel e Word). Boa "
            "comunicação, organização e proatividade. Interesse em aprender e se "
            "desenvolver nas áreas de RH e DP. Diferencial: experiência prévia em "
            "RH/DP. PCD."
        ),
    },
    {
        "titulo": "Estágio em Contabilidade",
        "descricao": (
            "Manaus/AM (Dom Pedro). Auxiliar na classificação e conciliação contábil "
            "de contas patrimoniais e de resultado. Apoiar na elaboração e "
            "conferência de lançamentos contábeis e relatórios financeiros. Auxiliar "
            "na organização e arquivamento de documentos fiscais e contábeis. Dar "
            "suporte nas rotinas de fechamento contábil e obrigações acessórias. "
            "Apoiar análises de balanço e demonstrações contábeis. Comunicação com "
            "setores internos e escritórios externos."
        ),
        "requisitos": (
            "Estar cursando Contabilidade (a partir do 3º período). Conhecimentos "
            "básicos em Pacote Office, especialmente Excel. Noções de lançamentos "
            "contábeis e conciliações. Boa comunicação, atenção aos detalhes e "
            "vontade de aprender."
        ),
    },
    {
        "titulo": "Estágio de Direito — Ações Trabalhistas",
        "descricao": (
            "Manaus/AM (Dom Pedro). Horário: 09h às 15h30 (intervalo de 30 min). "
            "Bolsa-auxílio: R$ 1.400,00. Benefícios: VT, Seguro de Vida e Plano "
            "Odontológico. Envio de notificações trabalhistas. Monitoramento de "
            "e-mails do setor jurídico. Consultas diárias ao site do DET. Solicitação "
            "de documentos para elaboração de defesas. Escrituração de eventos "
            "trabalhistas no eSocial. Integração de parcelas de acordos ao "
            "financeiro. Atualização do board de processos."
        ),
        "requisitos": (
            "Cursando Direito (a partir do 5º semestre). Interesse em Direito do "
            "Trabalho e Processual do Trabalho. Boa escrita e interpretação. Pacote "
            "Office. Desejável noções de peticionamento (PJe, e-SAJ)."
        ),
    },
    {
        "titulo": "Estagiário de Contrato — Direito",
        "descricao": (
            "Manaus/AM (Dom Pedro). Apoiar na execução de contratos administrativos: "
            "redação de ofícios, elaboração de planilhas e utilização das plataformas "
            "TOTVS e Monday. Organização, proatividade e vontade de aprender."
        ),
        "requisitos": (
            "Cursando Administração ou Direito (a partir do 3º período). Noções de "
            "licitação e contratos (diferencial). Pacote Office intermediário. "
            "Disponibilidade de horário. Perfil organizado e comunicativo. Boa "
            "escrita e oratória. Conhecimento no sistema TOTVS (diferencial)."
        ),
    },
    {
        "titulo": "Estagiário Financeiro",
        "descricao": (
            "Manaus/AM (Dom Pedro). Apoio às rotinas financeiras: controle de contas "
            "a pagar e a receber, elaboração de planilhas, conferência de documentos "
            "e utilização de sistemas como TOTVS e Monday. Proatividade, organização "
            "e interesse em aprender sobre gestão financeira."
        ),
        "requisitos": (
            "Cursando Administração ou Contabilidade (a partir do 3º período). "
            "Noções de gestão financeira (diferencial). Pacote Office intermediário. "
            "Disponibilidade de horário. Perfil organizado e comunicativo. Boa "
            "escrita e oratória. Conhecimento no sistema TOTVS (diferencial)."
        ),
    },
    {
        "titulo": "Estágio — Área de Tecnologia",
        "descricao": (
            "Manaus/AM (Dom Pedro). Estagiário talentoso para se juntar à equipe de "
            "tecnologia, com habilidades de comunicação e capacidade de pensar de "
            "forma lógica e estruturada. Ajudar a projetar, desenvolver e testar "
            "novas automações. Aprender sobre as últimas tendências em tecnologia. "
            "Ajudar a manter e atualizar as automações da empresa e criar novas."
        ),
        "requisitos": (
            "Cursando áreas de tecnologia e correlatas. Conhecimento em Make é "
            "diferencial. Excelentes habilidades de comunicação. Pensamento lógico e "
            "estruturado. Paixão por tecnologia. Vontade de aprender e crescer."
        ),
    },
    {
        "titulo": "Estagiário de T.I. (Foco em Desenvolvimento)",
        "descricao": (
            "Manaus/AM (Dom Pedro). Horário: 6h30min/dia (intervalo de 30min). "
            "Bolsa-auxílio: R$ 1.000,00 a R$ 1.400,00. Benefícios: VT, Seguro de "
            "Vida e Plano Odontológico. Auxiliar o time em projetos de backend. "
            "Participar de integrações de sistemas. Criar automações que facilitem "
            "o dia a dia."
        ),
        "requisitos": (
            "Cursando graduação na área de TI. Conhecimento em Python e Node. Boa "
            "base de lógica de programação. Noção de Banco de Dados. Diferencial: "
            "vontade de aprender e proatividade."
        ),
    },
    {
        "titulo": "Aprendiz de Marketing",
        "descricao": (
            "Manaus/AM (Dom Pedro). Apoiar na criação e divulgação de materiais de "
            "comunicação (posts, e-mails, folders). Auxiliar no gerenciamento das "
            "redes sociais e acompanhamento de métricas. Dar suporte na organização "
            "de eventos internos e ações de endomarketing. Atualizar planilhas e "
            "relatórios das campanhas e projetos do setor. Contribuir com ideias "
            "criativas para campanhas e conteúdos institucionais. Apoiar a equipe "
            "nas demandas administrativas do departamento."
        ),
        "requisitos": (
            "Estar cursando ensino médio. Interesse em aprender sobre marketing "
            "digital, redes sociais e comunicação corporativa. Conhecimentos básicos "
            "em Pacote Office (Word, Excel e PowerPoint). Boa comunicação escrita e "
            "verbal. Organização, proatividade e vontade de aprender. Idade entre "
            "18 e 22 anos. Diferencial: cursando ensino superior, noções de design "
            "(Canva, Photoshop), redes sociais e marketing digital."
        ),
    },
    {
        "titulo": "Auxiliar de Sistemas (SGI) — Backend Python",
        "descricao": (
            "Manaus/AM (Dom Pedro). Atuar como Auxiliar de Sistemas no time de "
            "tecnologia, com foco em desenvolvimento backend Python: APIs REST, "
            "automações, integrações entre sistemas, manutenção de aplicações em "
            "produção. Trabalho em equipe técnica para entregar soluções confiáveis."
        ),
        "requisitos": (
            "Obrigatórios: experiência sólida com Python (mínimo 1 ano), criação e "
            "manutenção de REST APIs (FastAPI, Flask ou Django), experiência com "
            "Make/Integromat, conhecimento em bancos de dados (PostgreSQL, MySQL), "
            "experiência com automação via Selenium, familiaridade com JavaScript "
            "e TypeScript. Desejáveis/Diferenciais: experiência com MongoDB, "
            "Hugging Face Transformers, LangChain, arquiteturas de microsserviços, "
            "noções de DevOps e CI/CD. PCD."
        ),
    },

    # ============================================================
    # LIDERANÇA / SUPERVISÃO
    # ============================================================
    {
        "titulo": "Encarregado de Serviços Gerais",
        "descricao": (
            "Manaus/AM. Realizar visitas diárias às unidades (UBS), garantindo "
            "presença e desempenho das equipes. Monitorar e reportar frequências, "
            "faltas e ocorrências à gestão administrativa. Estabelecer contato "
            "direto com os colaboradores, apoiando e orientando em campo. Facilitar "
            "a comunicação entre operação externa e setor administrativo interno. "
            "Contribuir ativamente para o bom funcionamento das rotinas operacionais."
        ),
        "requisitos": (
            "Ensino Médio completo. CNH A. Veículo próprio (motocicleta). "
            "Organização e disciplina no cumprimento de rotinas e prazos. "
            "Experiência anterior em cargos de liderança operacional ou supervisão "
            "de equipes. Boa comunicação, senso de responsabilidade e habilidade "
            "para resolução de problemas. Disponibilidade para deslocamentos diários."
        ),
    },
    {
        "titulo": "Encarregado de ASG",
        "descricao": (
            "Manaus/AM (Dom Pedro). Supervisor de Limpeza, Conservação e "
            "Higienização. Responsável por supervisionar e garantir a execução dos "
            "serviços de limpeza, conservação e higienização conforme as diretrizes "
            "da empresa. Exige uso de moto para transporte entre as unidades."
        ),
        "requisitos": (
            "Ensino Médio completo desejável. Experiência como supervisor de "
            "limpeza, conservação, higienização e asseio diário. Informática básica. "
            "Habilidades em liderança e comunicação assertiva. CNH A e veículo "
            "próprio (moto). Moto disponível para locação, seguindo dinâmica da "
            "empresa."
        ),
    },
    {
        "titulo": "Encarregado de ASG — Intermitente",
        "descricao": (
            "Manaus/AM (Dom Pedro). Contrato intermitente. Supervisor de Serviços "
            "Gerais para liderar equipes, monitorar operações, atender gestores, "
            "organizar treinamentos e apoiar o Departamento Pessoal."
        ),
        "requisitos": (
            "Ensino Médio completo. Experiência prévia. Informática básica. "
            "Habilidades em Liderança e comunicação assertiva. CNH A e veículo "
            "próprio (moto). Moto disponível para locação, seguindo dinâmica da "
            "empresa."
        ),
    },
    {
        "titulo": "Encarregado — TRE Paraíba",
        "descricao": (
            "João Pessoa/PB — posto TRE-PB. Escala semanal de 44h. Liderança e "
            "supervisão das equipes de Serviços Gerais e Limpeza no contrato público. "
            "Acompanhar rotinas, frequência, ocorrências e qualidade dos serviços "
            "com uso de sistemas informatizados (e-mail, planilhas, sistemas do "
            "TRE/TJ/TRT/MP)."
        ),
        "requisitos": (
            "Experiência comprovada na função de Encarregado(a), Supervisor(a) ou "
            "Líder de Serviços Gerais/Limpeza. Vivência em contratos públicos é "
            "diferencial (TRE, TJ, TRT, MP). Conhecimento do uso de sistemas "
            "informatizados (e-mail e outros). Conhecimento de produtos, "
            "equipamentos e técnicas de limpeza profissional. PCD."
        ),
    },
    {
        "titulo": "Encarregado — Hospital (João Pessoa)",
        "descricao": (
            "João Pessoa/PB — Hospital Universitário Lauro Wanderley. Escala semanal "
            "44h. Liderança operacional de equipe em ambiente hospitalar, com uso "
            "de sistemas informatizados (e-mail, controle de pessoal, logística "
            "hospitalar, transporte de pacientes)."
        ),
        "requisitos": (
            "Comprovação de experiência mínima de 6 meses em carteira ou prestação "
            "de serviço no cargo ou equivalente. Curso de nível intermediário de "
            "informática (Word, Excel, Internet). Conhecimento de sistemas "
            "informatizados (e-mail e outros). Noções de logística hospitalar e "
            "transporte de pacientes. Curso e experiência em atendimento ao cliente. "
            "PCD."
        ),
    },

    # ============================================================
    # SAÚDE — ATENDIMENTO HOSPITALAR
    # ============================================================
    {
        "titulo": "Atendente — Hospital (João Pessoa)",
        "descricao": (
            "João Pessoa/PB — Hospital Universitário Lauro Wanderley. Atendimento ao "
            "público em ambiente hospitalar. Escalas: Diurno 12x36 ou Noturno 12x36."
        ),
        "requisitos": (
            "Comprovação de experiência mínima de 6 meses em carteira ou prestação "
            "de serviço no cargo ou equivalente. Nível intermediário de informática "
            "(Word, Excel, Internet). Conhecimento de sistemas informatizados (e-mail), "
            "noções de logística hospitalar e transporte de pacientes. Curso em "
            "atendimento ao cliente. PCD."
        ),
    },
    {
        "titulo": "Maqueiro — Hospital (João Pessoa)",
        "descricao": (
            "João Pessoa/PB — Hospital Universitário Lauro Wanderley. Movimentação "
            "e transporte de pacientes no ambiente hospitalar. Escalas: Diurno "
            "12x36, Noturno 12x36 ou Semanal 44h."
        ),
        "requisitos": (
            "Comprovação de experiência mínima de 6 meses em carteira ou prestação "
            "de serviço no cargo ou equivalente. Capacitação básica de maqueiro "
            "abordando movimentação e transporte de pacientes. Certificação em "
            "primeiros socorros. PCD."
        ),
    },
    {
        "titulo": "Mensageiro / Motoboy — Hospital (João Pessoa)",
        "descricao": (
            "João Pessoa/PB — Hospital Universitário Lauro Wanderley. Função de "
            "mensageria e entrega utilizando moto. Escalas: Diurno 12x36, Noturno "
            "12x36 ou Semanal 44h."
        ),
        "requisitos": (
            "Comprovação de experiência mínima de 6 meses em carteira ou prestação "
            "de serviço no cargo ou equivalente. Nível intermediário de informática "
            "(Word, Excel, Internet). Curso em atendimento ao cliente. PCD."
        ),
    },
    {
        "titulo": "Motorista de Ambulância",
        "descricao": (
            "João Pessoa/PB — Hospital Universitário Lauro Wanderley. Escala "
            "Diurna 12x36. Atuar como motorista socorrista de ambulância."
        ),
        "requisitos": (
            "Comprovação de experiência mínima de 6 meses em carteira ou prestação "
            "de serviço. Carteira de habilitação D Motorista Socorrista. Treinamento "
            "especializado em socorrismo e reciclagem em cursos específicos a cada "
            "5 anos (art. 145-A, Lei nº 12.998/2014). Inscrição na CNH de que exerce "
            "atividade remunerada (EAR). PCD."
        ),
    },
    {
        "titulo": "Recepcionista",
        "descricao": (
            "Manaus/AM. Recepção e atendimento ao público. Atividades de portaria, "
            "atendimento presencial e telefônico, registro de visitantes e controle "
            "de acessos."
        ),
        "requisitos": (
            "Ensino Médio completo. Experiência em recepção, atendimento ao público "
            "ou atividades de portaria. Noções de informática (Word, Excel e e-mail). "
            "Boa comunicação, cordialidade, apresentação pessoal, discrição e empatia. "
            "Benefícios: VT, VR, Cesta Básica, Seguro de Vida, Plano Odontológico. PCD."
        ),
    },
    {
        "titulo": "Recepcionista — Intermitente (IFAM Tefé)",
        "descricao": (
            "Tefé/AM — IFAM Tefé. Contrato intermitente. Primeiro ponto de contato "
            "com clientes e visitantes, proporcionando experiência acolhedora e "
            "prestando apoio administrativo."
        ),
        "requisitos": (
            "Ensino médio completo (desejável superior em andamento). Experiência "
            "anterior como recepcionista ou em atendimento ao público é diferencial. "
            "Pacote Office, internet e e-mail. Boa comunicação verbal e escrita. "
            "Habilidade para múltiplas tarefas, apresentação pessoal impecável, "
            "postura profissional."
        ),
    },

    # ============================================================
    # MOTORISTAS
    # ============================================================
    {
        "titulo": "Motorista (Categoria B - geral)",
        "descricao": (
            "Manaus/AM (Dom Pedro). Vistoriar o veículo sob sua responsabilidade. "
            "Seguir normas de trânsito. Cumprir rotas pré-determinadas. Executar "
            "tarefas pertinentes à área. Comunicar falhas e providenciar reparos."
        ),
        "requisitos": (
            "Maior de 21 anos. Ensino médio completo. CNH B com no mínimo 2 anos. "
            "Não ter cassação de CNH. Não estar cumprindo pena de suspensão do "
            "direito de dirigir. PCD."
        ),
    },
    {
        "titulo": "Motorista Categoria B",
        "descricao": (
            "Manaus/AM. Condução de veículos leves. Experiência como motorista de "
            "veículos leves. Conhecimento em legislação de trânsito, mecânica "
            "preventiva e em transporte de pessoas/pequenas cargas."
        ),
        "requisitos": (
            "Ensino Fundamental completo. CNH Categoria B válida. Conhecimento em "
            "legislação de trânsito. Exame toxicológico atualizado. Noções de "
            "mecânica preventiva. Responsabilidade, atenção concentrada, organização "
            "e bom relacionamento. Benefícios: VT, VR, Cesta Básica, Seguro de Vida, "
            "Plano Odontológico. PCD."
        ),
    },
    {
        "titulo": "Motorista Categoria D",
        "descricao": (
            "Manaus/AM (Dom Pedro). Transporte de cargas diversas em rotas curtas e "
            "longas. Planejamento de itinerários para otimização das entregas. "
            "Inspeções diárias e manutenções básicas do veículo. Conferência de "
            "documentação. Cumprimento de normas de trânsito e segurança."
        ),
        "requisitos": (
            "Ensino médio completo. Experiência comprovada em carteira (CTPS). "
            "Carteira Nacional de Habilitação Categoria D (obrigatória). "
            "Documentação completa (incluindo dispensa militar quando aplicável)."
        ),
    },
]


def main() -> int:
    print(f"-> Conectando em {BASE} ...")
    existing = request("GET", "/api/jobs")
    print(f"   {len(existing)} vaga(s) existente(s)")

    for job in existing:
        request("DELETE", f"/api/jobs/{job['id']}")
        print(f"   removida: {job['titulo']}")

    print()
    print(f"-> Cadastrando {len(VAGAS)} vagas...")
    for vaga in VAGAS:
        try:
            created = request("POST", "/api/jobs", vaga)
            print(f"   OK  {created['titulo']}")
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="ignore")
            print(f"   ERRO  {vaga['titulo']} -> {err}")
            return 1
    print()
    print(f"Pronto. Total cadastrado: {len(VAGAS)} vagas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
