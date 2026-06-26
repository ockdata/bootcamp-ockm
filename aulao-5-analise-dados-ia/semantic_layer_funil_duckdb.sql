-- ============================================================
-- Camada semântica simples sobre funnel_eventos.csv
-- Demo: DuckDB + grafo semântico mínimo
-- ============================================================
--
-- Como rodar:
--   1. Coloque este arquivo .sql na mesma pasta do funnel_eventos.csv
--   2. Instale DuckDB: https://duckdb.org/docs/installation/
--   3. Rode:
--        duckdb aulao_funil.duckdb < semantic_layer_funil_duckdb.sql
--
-- O objetivo didático:
--   Bronze/Silver/Gold = dado organizado
--   Semantic = significado explícito para o agente/analista
--
-- ============================================================

-- ------------------------------------------------------------
-- BRONZE: lê o CSV exatamente como veio
-- ------------------------------------------------------------

CREATE OR REPLACE TABLE bronze_funnel_eventos AS
SELECT *
FROM read_csv_auto(
    'funnel_eventos.csv',
    header = true,
    all_varchar = true
);

-- ------------------------------------------------------------
-- SILVER: normaliza nomes, valores e timestamp
-- ------------------------------------------------------------

CREATE OR REPLACE TABLE silver_funnel_eventos AS
SELECT
    trim(user_id) AS user_id,
    lower(trim(plano)) AS plano,
    nullif(lower(trim(device)), '') AS device,
    lower(trim(etapa)) AS etapa,
    "timestamp" AS timestamp_raw,

    COALESCE(
        try_strptime("timestamp", '%d/%m/%Y %H:%M:%S'),
        try_strptime("timestamp", '%Y-%m-%d %H:%M:%S'),
        try_strptime("timestamp", '%Y-%m-%dT%H:%M:%S'),
        try_strptime("timestamp", '%Y/%m/%d %H:%M'),
        try_strptime("timestamp", '%d/%m/%Y'),
        try_strptime("timestamp", '%Y-%m-%d'),
        try_strptime("timestamp", '%Y/%m/%d')
    ) AS event_ts,

    CASE lower(trim(etapa))
        WHEN 'cadastro' THEN 1
        WHEN 'onboarding_inicio' THEN 2
        WHEN 'onboarding_completo' THEN 3
        WHEN 'ativacao' THEN 4
        WHEN 'exportacao' THEN 5
        ELSE NULL
    END AS stage_order

FROM bronze_funnel_eventos;

-- ------------------------------------------------------------
-- GOLD: uma linha por usuário com flags de etapa
-- ------------------------------------------------------------

CREATE OR REPLACE TABLE dim_usuario AS
SELECT
    user_id,
    min(plano) AS plano,
    coalesce(max(device), 'unknown') AS device,
    min(event_ts) AS first_event_ts,
    max(event_ts) AS last_event_ts,
    count(*) AS total_events
FROM silver_funnel_eventos
GROUP BY user_id;

CREATE OR REPLACE TABLE fct_user_funnel AS
SELECT
    user_id,

    max(CASE WHEN etapa = 'cadastro' THEN 1 ELSE 0 END) AS has_cadastro,
    max(CASE WHEN etapa = 'onboarding_inicio' THEN 1 ELSE 0 END) AS has_onboarding_inicio,
    max(CASE WHEN etapa = 'onboarding_completo' THEN 1 ELSE 0 END) AS has_onboarding_completo,
    max(CASE WHEN etapa = 'ativacao' THEN 1 ELSE 0 END) AS has_ativacao,
    max(CASE WHEN etapa = 'exportacao' THEN 1 ELSE 0 END) AS has_exportacao,

    min(CASE WHEN etapa = 'cadastro' THEN event_ts END) AS cadastro_ts,
    min(CASE WHEN etapa = 'onboarding_inicio' THEN event_ts END) AS onboarding_inicio_ts,
    min(CASE WHEN etapa = 'onboarding_completo' THEN event_ts END) AS onboarding_completo_ts,
    min(CASE WHEN etapa = 'ativacao' THEN event_ts END) AS ativacao_ts,
    min(CASE WHEN etapa = 'exportacao' THEN event_ts END) AS exportacao_ts

FROM silver_funnel_eventos
GROUP BY user_id;

CREATE OR REPLACE VIEW mart_funnel_segmentado AS
SELECT
    u.plano,
    u.device,

    count(*) AS usuarios,

    sum(f.has_cadastro) AS cadastro,
    sum(f.has_onboarding_inicio) AS onboarding_inicio,
    sum(f.has_onboarding_completo) AS onboarding_completo,
    sum(f.has_ativacao) AS ativacao,
    sum(f.has_exportacao) AS exportacao,

    round(100.0 * sum(f.has_onboarding_inicio) / nullif(sum(f.has_cadastro), 0), 1) AS pct_onboarding_inicio,
    round(100.0 * sum(f.has_onboarding_completo) / nullif(sum(f.has_cadastro), 0), 1) AS pct_onboarding_completo,
    round(100.0 * sum(f.has_ativacao) / nullif(sum(f.has_cadastro), 0), 1) AS pct_ativacao,
    round(100.0 * sum(f.has_exportacao) / nullif(sum(f.has_cadastro), 0), 1) AS pct_exportacao,

    round(100.0 * sum(f.has_onboarding_inicio) / nullif(sum(f.has_cadastro), 0), 1) AS trans_cadastro_to_onboarding_inicio,
    round(100.0 * sum(f.has_onboarding_completo) / nullif(sum(f.has_onboarding_inicio), 0), 1) AS trans_onboarding_inicio_to_onboarding_completo,
    round(100.0 * sum(f.has_ativacao) / nullif(sum(f.has_onboarding_completo), 0), 1) AS trans_onboarding_completo_to_ativacao,
    round(100.0 * sum(f.has_exportacao) / nullif(sum(f.has_ativacao), 0), 1) AS trans_ativacao_to_exportacao

FROM fct_user_funnel f
JOIN dim_usuario u USING (user_id)
GROUP BY u.plano, u.device;

-- ------------------------------------------------------------
-- SEMANTIC: grafo mínimo de significado
-- ------------------------------------------------------------

CREATE OR REPLACE TABLE semantic_nodes (
    node_id TEXT,
    node_type TEXT,
    label TEXT,
    physical_ref TEXT,
    description TEXT
);

INSERT INTO semantic_nodes VALUES
('entity_user', 'entity', 'Usuário', 'dim_usuario.user_id', 'Grão principal da análise: um usuário único no funil.'),
('entity_event', 'entity', 'Evento do funil', 'silver_funnel_eventos.etapa', 'Linha de evento emitida por usuário em uma etapa do funil.'),
('dim_plano', 'dimension', 'Plano', 'dim_usuario.plano', 'Dimensão de negócio que separa usuários free e pro.'),
('dim_device', 'dimension', 'Device', 'dim_usuario.device', 'Dimensão técnica/comportamental: web, ios ou android.'),
('dim_event_date', 'dimension', 'Data do evento', 'silver_funnel_eventos.event_ts', 'Data/hora normalizada do evento. O CSV original mistura formatos.'),
('stage_cadastro', 'stage', 'Cadastro', 'etapa = ''cadastro''', 'Primeira etapa do funil. Todo usuário esperado deve ter cadastro.'),
('stage_onboarding_inicio', 'stage', 'Onboarding iniciado', 'etapa = ''onboarding_inicio''', 'Usuário iniciou o onboarding.'),
('stage_onboarding_completo', 'stage', 'Onboarding completo', 'etapa = ''onboarding_completo''', 'Usuário concluiu o onboarding. É o evento de sucesso da métrica principal do aulão.'),
('stage_ativacao', 'stage', 'Ativação', 'etapa = ''ativacao''', 'Usuário chegou à ativação.'),
('stage_exportacao', 'stage', 'Exportação', 'etapa = ''exportacao''', 'Usuário concluiu exportação. Ajuda a revelar o problema de Pro no mobile.'),
('metric_onboarding_inicio_rate', 'metric', 'Taxa de início de onboarding', 'mart_funnel_segmentado.pct_onboarding_inicio', 'Usuários com onboarding_inicio dividido por usuários cadastrados.'),
('metric_onboarding_completo_rate', 'metric', 'Taxa de onboarding completo', 'mart_funnel_segmentado.pct_onboarding_completo', 'Usuários com onboarding_completo dividido por usuários cadastrados.'),
('metric_ativacao_rate', 'metric', 'Taxa de ativação', 'mart_funnel_segmentado.pct_ativacao', 'Usuários com ativacao dividido por usuários cadastrados.'),
('metric_exportacao_rate', 'metric', 'Taxa de exportação', 'mart_funnel_segmentado.pct_exportacao', 'Usuários com exportacao dividido por usuários cadastrados.'),
('metric_transicao_ativacao_exportacao', 'metric', 'Conversão ativação → exportação', 'mart_funnel_segmentado.trans_ativacao_to_exportacao', 'Usuários com exportacao dividido por usuários com ativacao.');

CREATE OR REPLACE TABLE semantic_edges (
    source_id TEXT,
    relation TEXT,
    target_id TEXT,
    confidence DOUBLE,
    description TEXT
);

INSERT INTO semantic_edges VALUES
('entity_user', 'HAS_DIMENSION', 'dim_plano', 1.0, 'Todo usuário pertence a um plano.'),
('entity_user', 'HAS_DIMENSION', 'dim_device', 1.0, 'Todo usuário deveria ter um device; há nulos no CSV.'),
('entity_user', 'EMITS', 'entity_event', 1.0, 'Usuários emitem eventos de funil.'),

('stage_onboarding_inicio', 'HAPPENS_AFTER', 'stage_cadastro', 1.0, 'Onboarding iniciado deve acontecer depois do cadastro.'),
('stage_onboarding_completo', 'HAPPENS_AFTER', 'stage_onboarding_inicio', 1.0, 'Onboarding completo deve acontecer depois do início do onboarding.'),
('stage_ativacao', 'HAPPENS_AFTER', 'stage_onboarding_completo', 1.0, 'Ativação deve acontecer depois do onboarding completo.'),
('stage_exportacao', 'HAPPENS_AFTER', 'stage_ativacao', 1.0, 'Exportação deve acontecer depois da ativação.'),

('metric_onboarding_inicio_rate', 'NUMERATOR_IS', 'stage_onboarding_inicio', 1.0, 'Numerador: usuários que chegaram em onboarding_inicio.'),
('metric_onboarding_inicio_rate', 'DENOMINATOR_IS', 'stage_cadastro', 1.0, 'Denominador: usuários cadastrados.'),
('metric_onboarding_inicio_rate', 'SHOULD_SEGMENT_BY', 'dim_plano', 1.0, 'Plano muda muito a interpretação da conversão.'),
('metric_onboarding_inicio_rate', 'SHOULD_SEGMENT_BY', 'dim_device', 0.9, 'Device pode indicar fricção de produto ou canal.'),

('metric_onboarding_completo_rate', 'NUMERATOR_IS', 'stage_onboarding_completo', 1.0, 'Numerador: usuários que concluíram onboarding.'),
('metric_onboarding_completo_rate', 'DENOMINATOR_IS', 'stage_cadastro', 1.0, 'Denominador: usuários cadastrados.'),
('metric_onboarding_completo_rate', 'SHOULD_SEGMENT_BY', 'dim_plano', 1.0, 'Sem segmentar por plano, o agregado esconde o problema dos usuários free.'),
('metric_onboarding_completo_rate', 'SHOULD_SEGMENT_BY', 'dim_device', 0.9, 'Ajuda a separar problema de perfil de usuário de problema de experiência.'),

('metric_ativacao_rate', 'NUMERATOR_IS', 'stage_ativacao', 1.0, 'Numerador: usuários ativados.'),
('metric_ativacao_rate', 'DENOMINATOR_IS', 'stage_cadastro', 1.0, 'Denominador: usuários cadastrados.'),
('metric_ativacao_rate', 'SHOULD_SEGMENT_BY', 'dim_plano', 1.0, 'Ativação varia fortemente entre free e pro.'),
('metric_ativacao_rate', 'SHOULD_SEGMENT_BY', 'dim_device', 0.9, 'Device ajuda a localizar fricção.'),

('metric_exportacao_rate', 'NUMERATOR_IS', 'stage_exportacao', 1.0, 'Numerador: usuários que exportaram.'),
('metric_exportacao_rate', 'DENOMINATOR_IS', 'stage_cadastro', 1.0, 'Denominador: usuários cadastrados.'),
('metric_exportacao_rate', 'SHOULD_SEGMENT_BY', 'dim_plano', 1.0, 'Exportação muda de padrão entre free e pro.'),
('metric_exportacao_rate', 'SHOULD_SEGMENT_BY', 'dim_device', 1.0, 'Ponto-chave: Pro em mobile parece travar em exportação.'),

('metric_transicao_ativacao_exportacao', 'NUMERATOR_IS', 'stage_exportacao', 1.0, 'Numerador: usuários que exportaram.'),
('metric_transicao_ativacao_exportacao', 'DENOMINATOR_IS', 'stage_ativacao', 1.0, 'Denominador: usuários ativados.'),
('metric_transicao_ativacao_exportacao', 'SHOULD_SEGMENT_BY', 'dim_plano', 1.0, 'Transição precisa ser vista por plano.'),
('metric_transicao_ativacao_exportacao', 'SHOULD_SEGMENT_BY', 'dim_device', 1.0, 'Transição precisa ser vista por device.');

CREATE OR REPLACE TABLE semantic_metrics (
    metric_id TEXT,
    label TEXT,
    numerator_node TEXT,
    denominator_node TEXT,
    grain TEXT,
    default_segments TEXT,
    business_question TEXT,
    interpretation_warning TEXT
);

INSERT INTO semantic_metrics VALUES
('metric_onboarding_inicio_rate', 'Taxa de início de onboarding', 'stage_onboarding_inicio', 'stage_cadastro', 'user_id', 'plano, device', 'Dos usuários cadastrados, quantos iniciaram onboarding?', 'Não analisar só agregado; segmentar por plano e device.'),
('metric_onboarding_completo_rate', 'Taxa de onboarding completo', 'stage_onboarding_completo', 'stage_cadastro', 'user_id', 'plano, device', 'Dos usuários cadastrados, quantos concluíram onboarding?', 'Métrica principal para mostrar que o agregado esconde o problema de Free.'),
('metric_ativacao_rate', 'Taxa de ativação', 'stage_ativacao', 'stage_cadastro', 'user_id', 'plano, device', 'Dos usuários cadastrados, quantos ativaram?', 'Comparar com onboarding_completo para identificar queda após onboarding.'),
('metric_exportacao_rate', 'Taxa de exportação', 'stage_exportacao', 'stage_cadastro', 'user_id', 'plano, device', 'Dos usuários cadastrados, quantos exportaram?', 'Boa para revelar queda de Pro mobile na etapa final.'),
('metric_transicao_ativacao_exportacao', 'Conversão ativação → exportação', 'stage_exportacao', 'stage_ativacao', 'user_id', 'plano, device', 'Dos usuários ativados, quantos exportaram?', 'Essa transição mostra com clareza o gargalo em mobile para usuários pro.');

CREATE OR REPLACE TABLE semantic_rules (
    rule_id TEXT,
    rule_type TEXT,
    expression TEXT,
    description TEXT,
    severity TEXT
);

INSERT INTO semantic_rules VALUES
('rule_stage_order', 'event_sequence', 'cadastro → onboarding_inicio → onboarding_completo → ativacao → exportacao', 'Se o usuário tem uma etapa posterior, deveria ter as anteriores.', 'warning'),
('rule_metric_denominator', 'metric_definition', 'Taxas de etapa usam usuários cadastrados como denominador padrão.', 'Evita confundir percentual sobre eventos com percentual sobre usuários.', 'critical'),
('rule_segment_before_conclusion', 'analysis', 'Toda métrica de funil deve ser primeiro analisada por plano e device.', 'Regra semântica central da demo: o agregado pode mentir.', 'critical'),
('rule_device_required', 'data_quality', 'device deveria estar preenchido para todo usuário.', 'Há valores nulos no CSV; trate como unknown ou exclua em análise específica.', 'warning'),
('rule_timestamp_mixed_formats', 'data_quality', 'timestamp precisa ser normalizado antes de análises temporais.', 'O arquivo contém múltiplos formatos de data/hora e alguns nulos.', 'warning');

-- ------------------------------------------------------------
-- Consultas para usar na demo
-- ------------------------------------------------------------

-- 1. O agregado
SELECT
    count(*) AS usuarios,
    sum(has_cadastro) AS cadastro,
    sum(has_onboarding_inicio) AS onboarding_inicio,
    sum(has_onboarding_completo) AS onboarding_completo,
    sum(has_ativacao) AS ativacao,
    sum(has_exportacao) AS exportacao,
    round(100.0 * sum(has_onboarding_inicio) / nullif(sum(has_cadastro), 0), 1) AS pct_onboarding_inicio,
    round(100.0 * sum(has_onboarding_completo) / nullif(sum(has_cadastro), 0), 1) AS pct_onboarding_completo,
    round(100.0 * sum(has_ativacao) / nullif(sum(has_cadastro), 0), 1) AS pct_ativacao,
    round(100.0 * sum(has_exportacao) / nullif(sum(has_cadastro), 0), 1) AS pct_exportacao
FROM fct_user_funnel;

-- 2. O segmentado, já seguindo a camada semântica
SELECT *
FROM mart_funnel_segmentado
ORDER BY plano, device;

-- 3. O que a camada semântica recomenda para uma métrica
SELECT
    metric.label AS metrica,
    e.relation AS relacao,
    target.label AS destino,
    target.node_type AS tipo,
    target.physical_ref,
    target.description
FROM semantic_edges e
JOIN semantic_nodes metric
    ON metric.node_id = e.source_id
JOIN semantic_nodes target
    ON target.node_id = e.target_id
WHERE e.source_id = 'metric_onboarding_completo_rate'
ORDER BY e.relation, target.label;

-- 4. Quais segmentos o agente deveria usar antes de concluir
SELECT
    target.label AS segmento_recomendado,
    target.physical_ref
FROM semantic_edges e
JOIN semantic_nodes target
    ON target.node_id = e.target_id
WHERE e.source_id = 'metric_onboarding_completo_rate'
  AND e.relation = 'SHOULD_SEGMENT_BY';

-- 5. Regra de negócio que você pode mostrar no aulão
SELECT *
FROM semantic_rules
WHERE rule_id = 'rule_segment_before_conclusion';

-- 6. Data quality útil para mostrar que IA também precisa desconfiar do dado
SELECT
    count(*) AS linhas,
    count(*) FILTER (WHERE device IS NULL) AS linhas_sem_device,
    count(*) FILTER (WHERE event_ts IS NULL) AS linhas_sem_timestamp_parseado
FROM silver_funnel_eventos;
