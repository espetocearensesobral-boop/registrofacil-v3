-- Registro Fácil — carga de demonstração com 20 processos completos
-- Compatível com SQLite e com o schema vigente da aplicação.
-- Uso recomendado: faça backup do banco antes de executar este arquivo.
-- O script é identificável pelo prefixo SEED-2026 e pode ser reaplicado sem duplicar processos.

PRAGMA foreign_keys = ON;
SAVEPOINT registrofacil_seed_20;

-- Garante que os catálogos utilizados existam mesmo em um banco recém-inicializado.
INSERT OR IGNORE INTO tipos_servico (nome, descricao, ativo, prazo_padrao) VALUES
    ('Abertura de Matrícula', 'Criação de nova matrícula de imóvel', 1, 30),
    ('Averbação', 'Averbação de documentos ou alterações em registros', 1, 30),
    ('Desmembramento', 'Desmembramento de área registrada', 1, 30),
    ('Escritura', 'Serviço de escritura pública', 1, 45),
    ('Registro', 'Registro de documentos ou imóveis', 1, 30),
    ('Retificação', 'Retificação de registro ou documento', 1, 90),
    ('RTD', 'Registro de Títulos e Documentos', 1, 10),
    ('RCPJ', 'Registro Civil de Pessoas Jurídicas', 1, 20);

INSERT OR IGNORE INTO status_processo (nome, hex_color, ativo) VALUES
    ('Aguardando Pagamento', '#ff7300', 1),
    ('Analisado', '#ffc107', 1),
    ('Finalizado', '#198754', 1),
    ('Pago', '#0d6efd', 1),
    ('Pendente Análise', '#dc3545', 1),
    ('Pendente Documentação', '#6c757d', 1),
    ('Prenotado', '#212529', 1),
    ('Retirado', '#d71dd1', 1);

-- Cadastros relacionados. Os nomes possuem prefixo próprio para facilitar limpeza posterior.
INSERT OR IGNORE INTO titulares (nome, telefone, email) VALUES
    ('SEED Ana Beatriz Moura', '(88) 99101-1001', 'ana.moura.seed@example.com'),
    ('SEED Bruno Carvalho Lima', '(88) 99101-1002', 'bruno.lima.seed@example.com'),
    ('SEED Camila Rocha Nunes', '(88) 99101-1003', 'camila.nunes.seed@example.com'),
    ('SEED Daniel Freitas Alves', '(88) 99101-1004', 'daniel.alves.seed@example.com'),
    ('SEED Eduarda Martins Sá', '(88) 99101-1005', 'eduarda.sa.seed@example.com'),
    ('SEED Felipe Gomes Araújo', '(88) 99101-1006', 'felipe.araujo.seed@example.com'),
    ('SEED Gabriela Torres Pinto', '(88) 99101-1007', 'gabriela.pinto.seed@example.com'),
    ('SEED Henrique Castro Melo', '(88) 99101-1008', 'henrique.melo.seed@example.com'),
    ('SEED Isabela Duarte Campos', '(88) 99101-1009', 'isabela.campos.seed@example.com'),
    ('SEED João Victor Barros', '(88) 99101-1010', 'joao.barros.seed@example.com'),
    ('SEED Larissa Mendes Costa', '(88) 99101-1011', 'larissa.costa.seed@example.com'),
    ('SEED Marcelo Ribeiro Farias', '(88) 99101-1012', 'marcelo.farias.seed@example.com'),
    ('SEED Natália Pires Lopes', '(88) 99101-1013', 'natalia.lopes.seed@example.com'),
    ('SEED Otávio Moraes Dias', '(88) 99101-1014', 'otavio.dias.seed@example.com'),
    ('SEED Patrícia Vasconcelos Reis', '(88) 99101-1015', 'patricia.reis.seed@example.com'),
    ('SEED Rafael Monteiro Braga', '(88) 99101-1016', 'rafael.braga.seed@example.com'),
    ('SEED Sabrina Oliveira Maia', '(88) 99101-1017', 'sabrina.maia.seed@example.com'),
    ('SEED Thiago Fernandes Queiroz', '(88) 99101-1018', 'thiago.queiroz.seed@example.com'),
    ('SEED Vitória Cardoso Freire', '(88) 99101-1019', 'vitoria.freire.seed@example.com'),
    ('SEED William Sales Moreira', '(88) 99101-1020', 'william.moreira.seed@example.com');

INSERT OR IGNORE INTO apresentantes (nome, telefone, email) VALUES
    ('SEED Cartório Boa Vista', '(88) 3677-2001', 'contato.boavista.seed@example.com'),
    ('SEED Imobiliária Horizonte', '(88) 3677-2002', 'documentos.horizonte.seed@example.com'),
    ('SEED Escritório Nobre & Associados', '(88) 3677-2003', 'protocolo.nobre.seed@example.com'),
    ('SEED Construtora Vale Azul', '(88) 3677-2004', 'juridico.valeazul.seed@example.com'),
    ('SEED Prefeitura Municipal', '(88) 3677-2005', 'protocolo.prefeitura.seed@example.com'),
    ('SEED Banco Regional', '(88) 3677-2006', 'registros.banco.seed@example.com'),
    ('SEED Marcelo Reis Advocacia', '(88) 3677-2007', 'contato.mreis.seed@example.com'),
    ('SEED Núcleo Empresarial Sobral', '(88) 3677-2008', 'registro.nucleo.seed@example.com');

-- 20 processos com combinações variadas de serviço, status, matrícula, prazo e notas.
INSERT OR IGNORE INTO processos (
    numero_processo, titular, titular_id, titular_telefone, titular_email,
    matricula, possui_matricula, tipo_id, data_entrada, status_id, prazo_final,
    apresentante, apresentante_id, apresentante_telefone, apresentante_email,
    responsavel_id, envolvido_notas, observacoes, data_conclusao
) VALUES
('SEED-2026-001', 'SEED Ana Beatriz Moura', (SELECT id FROM titulares WHERE nome='SEED Ana Beatriz Moura'), '(88) 99101-1001', 'ana.moura.seed@example.com', '654701', 1, (SELECT id FROM tipos_servico WHERE nome='Abertura de Matrícula'), date('now','-2 days'), (SELECT id FROM status_processo WHERE nome='Analisado'), date('now','+28 days'), 'SEED Cartório Boa Vista', (SELECT id FROM apresentantes WHERE nome='SEED Cartório Boa Vista'), '(88) 3677-2001', 'contato.boavista.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 0, 'Documentação inicial conferida e encaminhada para análise.', NULL),
('SEED-2026-002', 'SEED Bruno Carvalho Lima', (SELECT id FROM titulares WHERE nome='SEED Bruno Carvalho Lima'), '(88) 99101-1002', 'bruno.lima.seed@example.com', '654702', 1, (SELECT id FROM tipos_servico WHERE nome='Averbação'), date('now','-8 days'), (SELECT id FROM status_processo WHERE nome='Pendente Documentação'), date('now','+22 days'), 'SEED Imobiliária Horizonte', (SELECT id FROM apresentantes WHERE nome='SEED Imobiliária Horizonte'), '(88) 3677-2002', 'documentos.horizonte.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 1, 'Aguardando certidão atualizada do imóvel.', NULL),
('SEED-2026-003', 'SEED Camila Rocha Nunes', (SELECT id FROM titulares WHERE nome='SEED Camila Rocha Nunes'), '(88) 99101-1003', 'camila.nunes.seed@example.com', '654703', 1, (SELECT id FROM tipos_servico WHERE nome='Desmembramento'), date('now','-35 days'), (SELECT id FROM status_processo WHERE nome='Pendente Análise'), date('now','-5 days'), 'SEED Escritório Nobre & Associados', (SELECT id FROM apresentantes WHERE nome='SEED Escritório Nobre & Associados'), '(88) 3677-2003', 'protocolo.nobre.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 1, 'Processo com divergência na planta apresentada.', NULL),
('SEED-2026-004', 'SEED Daniel Freitas Alves', (SELECT id FROM titulares WHERE nome='SEED Daniel Freitas Alves'), '(88) 99101-1004', 'daniel.alves.seed@example.com', NULL, 0, (SELECT id FROM tipos_servico WHERE nome='Escritura'), date('now','-12 days'), (SELECT id FROM status_processo WHERE nome='Aguardando Pagamento'), date('now','+33 days'), 'SEED Construtora Vale Azul', (SELECT id FROM apresentantes WHERE nome='SEED Construtora Vale Azul'), '(88) 3677-2004', 'juridico.valeazul.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 0, 'Aguardando confirmação do pagamento dos emolumentos.', NULL),
('SEED-2026-005', 'SEED Eduarda Martins Sá', (SELECT id FROM titulares WHERE nome='SEED Eduarda Martins Sá'), '(88) 99101-1005', 'eduarda.sa.seed@example.com', '654705', 1, (SELECT id FROM tipos_servico WHERE nome='Registro'), date('now','-48 days'), (SELECT id FROM status_processo WHERE nome='Finalizado'), date('now','-18 days'), 'SEED Prefeitura Municipal', (SELECT id FROM apresentantes WHERE nome='SEED Prefeitura Municipal'), '(88) 3677-2005', 'protocolo.prefeitura.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 0, 'Registro concluído e documento liberado para retirada.', datetime('now','-18 days')),
('SEED-2026-006', 'SEED Felipe Gomes Araújo', (SELECT id FROM titulares WHERE nome='SEED Felipe Gomes Araújo'), '(88) 99101-1006', 'felipe.araujo.seed@example.com', '654706', 1, (SELECT id FROM tipos_servico WHERE nome='Retificação'), date('now','-70 days'), (SELECT id FROM status_processo WHERE nome='Retirado'), date('now','+20 days'), 'SEED Banco Regional', (SELECT id FROM apresentantes WHERE nome='SEED Banco Regional'), '(88) 3677-2006', 'registros.banco.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 0, 'Documento retirado pelo apresentante mediante protocolo.', datetime('now','-3 days')),
('SEED-2026-007', 'SEED Gabriela Torres Pinto', (SELECT id FROM titulares WHERE nome='SEED Gabriela Torres Pinto'), '(88) 99101-1007', 'gabriela.pinto.seed@example.com', '654707', 1, (SELECT id FROM tipos_servico WHERE nome='RTD'), date('now','-7 days'), (SELECT id FROM status_processo WHERE nome='Prenotado'), date('now','+3 days'), 'SEED Marcelo Reis Advocacia', (SELECT id FROM apresentantes WHERE nome='SEED Marcelo Reis Advocacia'), '(88) 3677-2007', 'contato.mreis.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 0, 'Prenotação realizada; aguardando conferência final.', NULL),
('SEED-2026-008', 'SEED Henrique Castro Melo', (SELECT id FROM titulares WHERE nome='SEED Henrique Castro Melo'), '(88) 99101-1008', 'henrique.melo.seed@example.com', NULL, 0, (SELECT id FROM tipos_servico WHERE nome='RCPJ'), date('now','-15 days'), (SELECT id FROM status_processo WHERE nome='Pago'), date('now','+5 days'), 'SEED Núcleo Empresarial Sobral', (SELECT id FROM apresentantes WHERE nome='SEED Núcleo Empresarial Sobral'), '(88) 3677-2008', 'registro.nucleo.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 1, 'Pagamento confirmado; documentação em conferência.', NULL),
('SEED-2026-009', 'SEED Isabela Duarte Campos', (SELECT id FROM titulares WHERE nome='SEED Isabela Duarte Campos'), '(88) 99101-1009', 'isabela.campos.seed@example.com', '654709', 1, (SELECT id FROM tipos_servico WHERE nome='Averbação'), date('now','-25 days'), (SELECT id FROM status_processo WHERE nome='Analisado'), date('now','+5 days'), 'SEED Cartório Boa Vista', (SELECT id FROM apresentantes WHERE nome='SEED Cartório Boa Vista'), '(88) 3677-2001', 'contato.boavista.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 0, 'Análise documental em andamento, sem pendências registradas.', NULL),
('SEED-2026-010', 'SEED João Victor Barros', (SELECT id FROM titulares WHERE nome='SEED João Victor Barros'), '(88) 99101-1010', 'joao.barros.seed@example.com', '654710', 1, (SELECT id FROM tipos_servico WHERE nome='Desmembramento'), date('now','-42 days'), (SELECT id FROM status_processo WHERE nome='Pendente Documentação'), date('now','-12 days'), 'SEED Imobiliária Horizonte', (SELECT id FROM apresentantes WHERE nome='SEED Imobiliária Horizonte'), '(88) 3677-2002', 'documentos.horizonte.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 1, 'Solicitada planta assinada e memorial descritivo revisado.', NULL),
('SEED-2026-011', 'SEED Larissa Mendes Costa', (SELECT id FROM titulares WHERE nome='SEED Larissa Mendes Costa'), '(88) 99101-1011', 'larissa.costa.seed@example.com', '654711', 1, (SELECT id FROM tipos_servico WHERE nome='Abertura de Matrícula'), date('now','-1 day'), (SELECT id FROM status_processo WHERE nome='Aguardando Pagamento'), date('now','+29 days'), 'SEED Prefeitura Municipal', (SELECT id FROM apresentantes WHERE nome='SEED Prefeitura Municipal'), '(88) 3677-2005', 'protocolo.prefeitura.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 0, 'Novo protocolo aguardando pagamento inicial.', NULL),
('SEED-2026-012', 'SEED Marcelo Ribeiro Farias', (SELECT id FROM titulares WHERE nome='SEED Marcelo Ribeiro Farias'), '(88) 99101-1012', 'marcelo.farias.seed@example.com', '654712', 1, (SELECT id FROM tipos_servico WHERE nome='Registro'), date('now','-20 days'), (SELECT id FROM status_processo WHERE nome='Analisado'), date('now','+10 days'), 'SEED Banco Regional', (SELECT id FROM apresentantes WHERE nome='SEED Banco Regional'), '(88) 3677-2006', 'registros.banco.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 0, 'Conferência dos documentos de garantia iniciada.', NULL),
('SEED-2026-013', 'SEED Natália Pires Lopes', (SELECT id FROM titulares WHERE nome='SEED Natália Pires Lopes'), '(88) 99101-1013', 'natalia.lopes.seed@example.com', NULL, 0, (SELECT id FROM tipos_servico WHERE nome='Escritura'), date('now','-50 days'), (SELECT id FROM status_processo WHERE nome='Finalizado'), date('now','-5 days'), 'SEED Escritório Nobre & Associados', (SELECT id FROM apresentantes WHERE nome='SEED Escritório Nobre & Associados'), '(88) 3677-2003', 'protocolo.nobre.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 0, 'Escritura registrada e processo encerrado.', datetime('now','-5 days')),
('SEED-2026-014', 'SEED Otávio Moraes Dias', (SELECT id FROM titulares WHERE nome='SEED Otávio Moraes Dias'), '(88) 99101-1014', 'otavio.dias.seed@example.com', '654714', 1, (SELECT id FROM tipos_servico WHERE nome='Retificação'), date('now','-80 days'), (SELECT id FROM status_processo WHERE nome='Pendente Análise'), date('now','+10 days'), 'SEED Construtora Vale Azul', (SELECT id FROM apresentantes WHERE nome='SEED Construtora Vale Azul'), '(88) 3677-2004', 'juridico.valeazul.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 1, 'Aguardando parecer técnico sobre a divergência cadastral.', NULL),
('SEED-2026-015', 'SEED Patrícia Vasconcelos Reis', (SELECT id FROM titulares WHERE nome='SEED Patrícia Vasconcelos Reis'), '(88) 99101-1015', 'patricia.reis.seed@example.com', '654715', 1, (SELECT id FROM tipos_servico WHERE nome='RTD'), date('now','-3 days'), (SELECT id FROM status_processo WHERE nome='Pago'), date('now','+7 days'), 'SEED Cartório Boa Vista', (SELECT id FROM apresentantes WHERE nome='SEED Cartório Boa Vista'), '(88) 3677-2001', 'contato.boavista.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 0, 'Pagamento identificado e título encaminhado ao setor responsável.', NULL),
('SEED-2026-016', 'SEED Rafael Monteiro Braga', (SELECT id FROM titulares WHERE nome='SEED Rafael Monteiro Braga'), '(88) 99101-1016', 'rafael.braga.seed@example.com', '654716', 1, (SELECT id FROM tipos_servico WHERE nome='RCPJ'), date('now','-18 days'), (SELECT id FROM status_processo WHERE nome='Prenotado'), date('now','+2 days'), 'SEED Núcleo Empresarial Sobral', (SELECT id FROM apresentantes WHERE nome='SEED Núcleo Empresarial Sobral'), '(88) 3677-2008', 'registro.nucleo.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 1, 'Aguardando validação da documentação societária.', NULL),
('SEED-2026-017', 'SEED Sabrina Oliveira Maia', (SELECT id FROM titulares WHERE nome='SEED Sabrina Oliveira Maia'), '(88) 99101-1017', 'sabrina.maia.seed@example.com', NULL, 0, (SELECT id FROM tipos_servico WHERE nome='Abertura de Matrícula'), date('now','-30 days'), (SELECT id FROM status_processo WHERE nome='Finalizado'), date('now','-2 days'), 'SEED Prefeitura Municipal', (SELECT id FROM apresentantes WHERE nome='SEED Prefeitura Municipal'), '(88) 3677-2005', 'protocolo.prefeitura.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 0, 'Matrícula aberta e conferida pelo setor de registro.', datetime('now','-2 days')),
('SEED-2026-018', 'SEED Thiago Fernandes Queiroz', (SELECT id FROM titulares WHERE nome='SEED Thiago Fernandes Queiroz'), '(88) 99101-1018', 'thiago.queiroz.seed@example.com', '654718', 1, (SELECT id FROM tipos_servico WHERE nome='Averbação'), date('now','-60 days'), (SELECT id FROM status_processo WHERE nome='Retirado'), date('now','+5 days'), 'SEED Marcelo Reis Advocacia', (SELECT id FROM apresentantes WHERE nome='SEED Marcelo Reis Advocacia'), '(88) 3677-2007', 'contato.mreis.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 0, 'Averbação concluída e documento retirado.', datetime('now','-1 day')),
('SEED-2026-019', 'SEED Vitória Cardoso Freire', (SELECT id FROM titulares WHERE nome='SEED Vitória Cardoso Freire'), '(88) 99101-1019', 'vitoria.freire.seed@example.com', '654719', 1, (SELECT id FROM tipos_servico WHERE nome='Registro'), date('now','-9 days'), (SELECT id FROM status_processo WHERE nome='Pendente Documentação'), date('now','+21 days'), 'SEED Imobiliária Horizonte', (SELECT id FROM apresentantes WHERE nome='SEED Imobiliária Horizonte'), '(88) 3677-2002', 'documentos.horizonte.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 1, 'Pendente cópia autenticada do documento de identificação.', NULL),
('SEED-2026-020', 'SEED William Sales Moreira', (SELECT id FROM titulares WHERE nome='SEED William Sales Moreira'), '(88) 99101-1020', 'william.moreira.seed@example.com', '654720', 1, (SELECT id FROM tipos_servico WHERE nome='Desmembramento'), date('now','-28 days'), (SELECT id FROM status_processo WHERE nome='Analisado'), date('now','+2 days'), 'SEED Construtora Vale Azul', (SELECT id FROM apresentantes WHERE nome='SEED Construtora Vale Azul'), '(88) 3677-2004', 'juridico.valeazul.seed@example.com', (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1), 0, 'Análise final da planta e dos documentos de propriedade.', NULL);

-- Atualiza o último registro conhecido de cada titular incluído na carga.
UPDATE titulares
SET ultimo_registro_id = (
    SELECT p.id FROM processos p
    WHERE p.titular_id = titulares.id
    ORDER BY p.data_entrada DESC, p.id DESC
    LIMIT 1
)
WHERE nome LIKE 'SEED %';

-- Histórico inicial para cada processo de demonstração. Reaplicar o script não duplica estes eventos.
DELETE FROM historico_processos
WHERE processo_id IN (SELECT id FROM processos WHERE numero_processo LIKE 'SEED-2026-%');

INSERT INTO historico_processos (
    processo_id, usuario_id, campo_alterado, valor_antigo, valor_novo,
    observacao_adicional, timestamp_alteracao
)
SELECT
    p.id,
    (SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1),
    'Carga de demonstração',
    NULL,
    'Processo criado',
    'Registro inserido pelo script data/seed_20_processos.sql.',
    datetime('now','localtime')
FROM processos p
WHERE p.numero_processo LIKE 'SEED-2026-%';

RELEASE SAVEPOINT registrofacil_seed_20;

-- Conferência rápida após a execução:
-- SELECT COUNT(*) AS processos_seed FROM processos WHERE numero_processo LIKE 'SEED-2026-%';
-- SELECT status_id, COUNT(*) FROM processos WHERE numero_processo LIKE 'SEED-2026-%' GROUP BY status_id;
-- SELECT COUNT(*) AS historicos_seed FROM historico_processos h JOIN processos p ON p.id=h.processo_id WHERE p.numero_processo LIKE 'SEED-2026-%';
