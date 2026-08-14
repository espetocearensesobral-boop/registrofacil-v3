// registrofacil/static/js/processos/form_logic.js

import { showToast, formatBytes, isValidEmail, isValidPhone, isValidMatricula, formatPhoneNumber } from '../utils/dom_helpers.js';

export function initializeProcessFormLogic(FlaskRoutes) {
    console.log("Executando initializeProcessFormLogic...");

    const formProcesso = document.getElementById('form-processo');

    if (!formProcesso) {
        console.error("ERRO CRÍTICO: Formulário 'form-processo' NÃO ENCONTRADO no DOM! O listener de submit não será anexado.");
        return;
    }
    console.log("Formulário 'form-processo' ENCONTRADO. Anexando event listener...");

    const loadingOverlay = document.getElementById('loading-overlay');
    const fileUploadArea = document.getElementById('file-upload-area');
    const fileInput = document.getElementById('anexos');
    const filePreview = document.getElementById('file-preview');
    const totalSizeDiv = document.getElementById('total-size');
    const observacoesField = document.getElementById('observacoes');
    const observacoesCounter = document.getElementById('observacoes-counter');

    const processIdInfo = document.getElementById('process-id-info');

    const MAX_OBS_CHARS = 5000;
    const MAX_OBS_LINES = 50;
    let currentFiles = [];

    const firstField = document.getElementById('titular');
    if (firstField) { firstField.focus(); }

    // Add keyboard navigation (Enter key)
    const formInputs = Array.from(formProcesso.querySelectorAll('input:not([type="hidden"]), select, textarea, button:not([type="button"])'));
    formInputs.forEach((input, index) => {
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && this.type !== 'textarea') {
                e.preventDefault();
                let nextIndex = index + 1;
                while (nextIndex < formInputs.length) {
                    const nextInput = formInputs[nextIndex];
                    if (nextInput && !nextInput.disabled && !nextInput.readOnly && nextInput.tabIndex !== -1) {
                        nextInput.focus();
                        return;
                    }
                    nextIndex++;
                }
                // Se não houver próximo campo, submete o formulário
                const submitBtn = formProcesso.querySelector('button[type="submit"]');
                if (submitBtn) {
                    submitBtn.click();
                } else {
                    formProcesso.submit();
                }
            }
        });

        // Padronizar em maiúsculo (exceto observações e campos específicos como e-mail)
        if (input.tagName === 'INPUT' && input.type === 'text' && input.id !== 'apresentante_email') {
            input.addEventListener('input', function() {
                const start = this.selectionStart;
                const end = this.selectionEnd;
                this.value = this.value.toUpperCase();
                this.setSelectionRange(start, end);
            });
        }
    });

    // Add validation listeners
    const fieldsToValidateOnEvent = [ 'titular', 'tipo_servico', 'matricula', 'status', 'apresentante_email', 'apresentante_telefone', 'data_entrada' ];
    fieldsToValidateOnEvent.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.addEventListener('blur', validateField);
            field.addEventListener('input', validateField);
        }
    });

    // Observations counter
    if (observacoesField) {
        observacoesField.addEventListener('input', updateObservacoesCounter);
        updateObservacoesCounter();
    }
    function updateObservacoesCounter() {
        let text = observacoesField.value; // Use 'let' para que o valor possa ser alterado.
        
        // --- INÍCIO DA ALTERAÇÃO DO BLOQUEIO DE DIGITAÇÃO ---
        
        // Caracteres úteis (sem espaços)
        let textWithoutSpaces = text.replace(/\s/g, '');
        
        // Variáveis para a lógica de corte
        let charCount = textWithoutSpaces.length;
        let lineCount = (text.match(/\n/g) || []).length + 1;
        
        // 1. Lógica de corte (Bloqueio de digitação de caracteres ÚTEIS)
        if (textWithoutSpaces.length > MAX_OBS_CHARS) {
            let allowedText = '';
            let currentUsefulCount = 0;
            let limitReached = false;
            
            // Itera sobre o texto original e reconstrói a string até atingir 500 caracteres ÚTEIS.
            for (const char of text) {
                if (/\s/.test(char)) {
                    // Adiciona espaços/quebras de linha normalmente.
                    allowedText += char;
                } else {
                    // Adiciona o caractere útil somente se o contador for menor que o máximo.
                    if (currentUsefulCount < MAX_OBS_CHARS) {
                        allowedText += char;
                        currentUsefulCount++;
                    } else {
                        // Se o contador atingiu 500, ignora este caractere útil.
                        limitReached = true;
                    }
                }
            }

            // Atualiza o valor do campo de texto com o texto cortado
            observacoesField.value = allowedText;
            text = allowedText; // Atualiza a variável local 'text'
            textWithoutSpaces = allowedText.replace(/\s/g, ''); // Recalcula (deve ser 500)
            charCount = textWithoutSpaces.length; // Usa o valor final (máx. 500)
            
            if (limitReached) {
                 showToast('warning', `Limite máximo de ${MAX_OBS_CHARS} caracteres úteis atingido.`);
            }
        }
        
        // 2. Lógica de corte (Bloqueio de digitação de LINHAS)
        if (lineCount > MAX_OBS_LINES) {
            // Corta as linhas excedentes (mantendo apenas o número máximo de linhas)
            const lines = text.split('\n').slice(0, MAX_OBS_LINES);
            observacoesField.value = lines.join('\n');
            text = observacoesField.value;
            lineCount = MAX_OBS_LINES;
            
            showToast('warning', `Limite máximo de ${MAX_OBS_LINES} linhas atingido.`);
        }
        
        // --- FIM DA ALTERAÇÃO DO BLOQUEIO DE DIGITAÇÃO ---
        
        // Recalcula lineCount após o corte de linhas
        lineCount = (text.match(/\n/g) || []).length + 1;


        observacoesCounter.textContent = `${charCount} caracteres (sem espaços), ${lineCount} linhas (Máx: ${MAX_OBS_CHARS} caracteres, ${MAX_OBS_LINES} linhas)`;

        if (charCount > MAX_OBS_CHARS || lineCount > MAX_OBS_LINES) {
            observacoesCounter.classList.add('text-danger');
            observacoesField.classList.add('is-invalid');
        } else {
            observacoesCounter.classList.remove('text-danger');
            observacoesField.classList.remove('is-invalid');
        }
    }

    // Generic field validation function
    function validateField() {
        const field = this;
        const value = field.value.trim();
        field.classList.remove('is-invalid', 'is-valid');
        let isValid = true;
        let feedbackMessage = '';
        const feedbackDiv = field.parentNode.querySelector('.invalid-feedback');

        if (field.required && !value) {
            isValid = false;
            feedbackMessage = 'Este campo é obrigatório.';
        }
        else if (field.type === 'email' && value && !isValidEmail(value)) {
            isValid = false;
            feedbackMessage = 'Por favor, informe um e-mail válido.';
        } else if (field.type === 'tel' && value) {
            const cleanedValue = value.replace(/\D/g, '');
            if (cleanedValue.length > 0 && (cleanedValue.length < 10 || cleanedValue.length > 11)) {
                isValid = false;
                feedbackMessage = 'Telefone inválido (mín. 10, máx. 11 dígitos, incluindo DDD).';
            } else if (cleanedValue.length > 0 && !isValidPhone(value)) {
                isValid = false;
                feedbackMessage = 'Formato inválido. Ex: (XX) 9XXXX-XXXX ou (XX) XXXX-XXXX.';
            }
        }
        else if (field.id === 'matricula' && value && !isValidMatricula(value)) {
            isValid = false;
            feedbackMessage = 'Matrícula inválida. Use apenas letras, números, espaços, hífens, pontos e barras (1-50 caracteres).';
        }
        else if (field.id === 'data_entrada' && field.required && !value) {
            isValid = false;
            feedbackMessage = 'Por favor, informe a data de entrada.';
        }


        if (!isValid) {
            field.classList.add('is-invalid');
            if (feedbackDiv) {
                feedbackDiv.textContent = feedbackMessage;
            }
        } else if (value) {
            field.classList.add('is-valid');
        }
    }

    // Phone field specific listener
    const telefoneField = document.getElementById('apresentante_telefone');
    if (telefoneField) {
        telefoneField.addEventListener('input', function() {
            const currentCursorPos = this.selectionStart;
            const originalLength = this.value.length;

            const oldValue = this.value.replace(/\D/g, '');
            this.value = formatPhoneNumber(oldValue);

            const newLength = this.value.length;
            let newCursorPos = currentCursorPos + (newLength - originalLength);

            if (newCursorPos < newLength) {
                const char = this.value.charAt(newCursorPos - 1);
                if (char === '(' || char === ' ' || char === '-') {
                    newCursorPos++;
                }
            }
            this.setSelectionRange(newCursorPos, newCursorPos);
            
            validateField.call(this);
        });

        if (telefoneField.value) {
            telefoneField.value = formatPhoneNumber(telefoneField.value);
            validateField.call(telefoneField);
        }
    }

    // --- File Upload and Preview Logic (Moved functions to higher scope) ---
    const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024;
    const ALLOWED_EXTENSIONS_JS = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'txt', 'xlsx', 'xls', 'csv'];

    // Funções de Anexo agora definidas no escopo de initializeProcessFormLogic
    function addFiles(newFiles) {
        for (let i = 0; i < newFiles.length; i++) {
            const file = newFiles[i];
            const isDuplicate = currentFiles.some((existingFile) => existingFile.name === file.name && existingFile.size === file.size );
            if (!isDuplicate) {
                currentFiles.push(file);
            }
        }
        renderFilePreviews();
    }

    function removeFile(index) {
        currentFiles.splice(index, 1);
        renderFilePreviews();
    }

    function renderFilePreviews() {
        filePreview.innerHTML = '';
        if (currentFiles.length === 0) {
            filePreview.classList.add('d-none');
            totalSizeDiv.textContent = '';
            return;
        }
        filePreview.classList.remove('d-none');
        let totalSize = 0;

        currentFiles.forEach((file, index) => {
            totalSize += file.size;
            const fileBadge = document.createElement('div');
            fileBadge.className = 'file-badge';

            const icon = document.createElement('i');
            const ext = file.name.split('.').pop()?.toLowerCase() || '';

            const iconClasses = {
                'pdf': 'bi-file-earmark-pdf-fill', 'doc': 'bi-file-earmark-word-fill',
                'docx': 'bi-file-earmark-word-fill', 'jpg': 'bi-file-earmark-image-fill',
                'jpeg': 'bi-file-earmark-image-fill', 'png': 'bi-file-earmark-image-fill',
                'gif': 'bi-file-earmark-image-fill', 'txt': 'bi-file-earmark-text-fill',
                'xlsx': 'bi-file-earmark-excel-fill', 'xls': 'bi-file-earmark-excel-fill',
                'csv': 'bi-file-earmark-spreadsheet-fill'
            };
            const colorClasses = {
                'pdf': 'text-danger', 'doc': 'text-primary', 'docx': 'text-primary',
                'jpg': 'text-success', 'jpeg': 'text-success', 'png': 'text-success',
                'gif': 'text-success', 'txt': 'text-secondary',
                'xlsx': 'text-success', 'xls': 'text-success', 'csv': 'text-info'
            };
            icon.className = 'bi ' + (iconClasses[ext] || 'bi-file-earmark-fill') + ' ' + (colorClasses[ext] || 'text-muted');

            const fileNameSpan = document.createElement('span');
            fileNameSpan.textContent = file.name.length > 20 ? file.name.substring(0, 17) + '...' + file.name.substring(file.name.length - 4) : file.name;

            const removeButton = document.createElement('button');
            removeButton.className = 'btn-close ms-2';
            removeButton.setAttribute('type', 'button');
            removeButton.setAttribute('aria-label', 'Remover arquivo');
            removeButton.onclick = (e) => {
                e.stopPropagation();
                removeFile(index);
            };

            let isFileValid = true;
            if (file.size > MAX_FILE_SIZE_BYTES) {
                fileBadge.classList.add('error');
                fileNameSpan.textContent += ` (>${(MAX_FILE_SIZE_BYTES / (1024 * 1024)).toFixed(0)}MB)`;
                isFileValid = false;
            }
            if (!ALLOWED_EXTENSIONS_JS.includes(ext)) {
                fileBadge.classList.add('error');
                fileNameSpan.textContent += ' (Extensão inválida)';
                isFileValid = false;
            }
            if (isFileValid) {
                fileBadge.classList.add('success');
            }

            fileBadge.appendChild(icon);
            fileBadge.appendChild(fileNameSpan);
            fileBadge.appendChild(removeButton);
            filePreview.appendChild(fileBadge);
        });
        totalSizeDiv.innerHTML = `Total: ${formatBytes(totalSize)} (${currentFiles.length} arquivo${currentFiles.length !== 1 ? 's' : ''})`;
    }

    // Anexar listeners de arquivo apenas se os elementos existirem
    if (fileUploadArea && fileInput) {
        fileUploadArea.addEventListener('dragover', function(e) { e.preventDefault(); this.classList.add('dragover'); });
        fileUploadArea.addEventListener('dragleave', function(e) { e.preventDefault(); this.classList.remove('dragover'); });
        fileUploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                addFiles(e.dataTransfer.files);
            }
        });

        fileInput.addEventListener('change', function() {
            addFiles(this.files);
            this.value = ''; // Limpar o valor do input para permitir upload do mesmo arquivo novamente
        });
    }
    
    // Existing attachments logic (for editar.html)
    const selectAllExistingAnexosCheckbox = document.getElementById('selectAllExistingAnexos');
    const existingAnexoCheckboxes = document.querySelectorAll('.existing-anexo-checkbox');
    const selectedAnexosCountElement = document.getElementById('selectedAnexosCount');

    if (selectAllExistingAnexosCheckbox && existingAnexoCheckboxes && selectedAnexosCountElement) {
        selectAllExistingAnexosCheckbox.addEventListener('change', function() {
            existingAnexoCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            updateSelectedAnexosCount();
        });
        existingAnexoCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', updateSelectedAnexosCount);
        });

        function updateSelectedAnexosCount() {
            const checkedCount = document.querySelectorAll('.existing-anexo-checkbox:checked').length;
            const totalCount = existingAnexoCheckboxes.length;
            selectedAnexosCountElement.textContent = `Selecionados: ${checkedCount} de ${totalCount}`;

            if (totalCount === 0) {
                selectAllExistingAnexosCheckbox.checked = false;
                selectAllExistingAnexosCheckbox.indeterminate = false;
                selectAllExistingAnexosCheckbox.disabled = true;
            } else if (checkedCount === totalCount) {
                selectAllExistingAnexosCheckbox.checked = true;
                selectAllExistingAnexosCheckbox.indeterminate = false;
                selectAllExistingAnexosCheckbox.disabled = false;
            } else if (checkedCount > 0) {
                selectAllExistingAnexosCheckbox.checked = false;
                selectAllExistingAnexosCheckbox.indeterminate = true;
                selectAllExistingAnexosCheckbox.disabled = false;
            } else {
                selectAllExistingAnexosCheckbox.checked = false;
                selectAllExistingAnexosCheckbox.indeterminate = false;
                selectAllExistingAnexosCheckbox.disabled = false;
            }
        }
        updateSelectedAnexosCount();
    }


    // --- Form Submission Logic (AJAX) ---
    formProcesso.addEventListener('submit', async function(e) {
        console.log("DEBUG: Evento de submit do formulário acionado.");
        try {
            e.preventDefault();
            e.stopPropagation();

            console.log("DEBUG: Default preventido. Validando campos do formulário.");

            formProcesso.classList.remove('was-validated');
            formProcesso.querySelectorAll('.is-invalid, .is-valid').forEach(el => {
                el.classList.remove('is-invalid', 'is-valid');
            });

            let allFieldsValid = true;
            const fieldsToValidateOnSubmit = formProcesso.querySelectorAll('input[required], select[required], textarea[required], input[type="email"], input[type="tel"], #matricula, #data_entrada');

            fieldsToValidateOnSubmit.forEach(field => {
                validateField.call(field);
                if (field.classList.contains('is-invalid')) {
                    allFieldsValid = false;
                }
            });

            const prazoFinalField = document.getElementById('prazo_final');
            if (prazoFinalField && prazoFinalField.value.trim() !== '') {
                validateField.call(prazoFinalField);
                if (prazoFinalField.classList.contains('is-invalid')) {
                    allFieldsValid = false;
                }
            }


            const obsText = observacoesField ? observacoesField.value : '';
            // --- ATENÇÃO: Corrigido o cálculo para usar a nova lógica (sem espaços) no submit ---
            const obsCharCount = obsText.replace(/\s/g, '').length;
            // --- FIM DA CORREÇÃO ---
            const obsLineCount = (obsText.match(/\n/g) || []).length + 1;

            if (obsCharCount > MAX_OBS_CHARS || obsLineCount > MAX_OBS_LINES) {
                allFieldsValid = false;
                observacoesField.classList.add('is-invalid');
                showToast('danger', `As observações excedem o limite de ${MAX_OBS_CHARS} caracteres (sem espaços) ou ${MAX_OBS_LINES} linhas.`);
                if (observacoesField) {
                    observacoesField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    observacoesField.focus();
                }
                return;
            }

            if (!allFieldsValid) {
                formProcesso.classList.add('was-validated');
                const firstInvalidField = formProcesso.querySelector('.is-invalid');
                if (firstInvalidField) {
                    firstInvalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    firstInvalidField.focus();
                }
                showToast('danger', 'Por favor, corrija os campos destacados. Alguns campos obrigatórios não foram preenchidos ou estão inválidos.');
                return;
            }

            console.log("DEBUG: Mostrando loading overlay antes da requisição Fetch.");
            if (loadingOverlay) { loadingOverlay.style.display = 'flex'; }

            const formData = new FormData(formProcesso);
            formData.delete('anexos[]'); // Remove o input file original, pois vamos adicionar os arquivos de currentFiles

            currentFiles.forEach(file => {
                formData.append('anexos[]', file);
            });

            try {
                console.log("DEBUG: Iniciando requisição Fetch para: ", formProcesso.action);
                const response = await fetch(formProcesso.action, {
                    method: formProcesso.method,
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                const contentType = response.headers.get("content-type");
                let data = {};

                // CORREÇÃO v3.2.3: Parsear JSON independentemente do status (response.ok removido)
                // O servidor pode retornar JSON válido mesmo com status 400, 500, etc.
                if (contentType && contentType.includes("application/json")) {
                    try {
                        data = await response.json();
                        console.log('DEBUG: Dados JSON recebidos (status:', response.status, '):', data);
                    }
                    catch (jsonError) {
                        console.error('ERRO: Erro ao parsear JSON da resposta (Content-Type JSON, mas corpo inválido):', jsonError);
                        showToast('danger', 'Ocorreu um erro na comunicação: resposta JSON inválida do servidor.');
                        return;
                    }
                }
                else {
                    const errorText = await response.text();
                    console.error('ERRO: Resposta não JSON ou Content-Type ausente/incorreto. Conteúdo:', errorText);
                    showToast('danger', `Ocorreu um erro na comunicação com o servidor. Resposta inválida. Status: ${response.status}`);
                    return;
                }

                if (response.ok) {
                    console.log('DEBUG: API Response (Sucesso):', data);

                    if (data.success) {
                        showToast('success', data.message);

                        console.log("DEBUG: Escondendo loading overlay explicitamente antes de exibir o modal/redirecionar.");
                        if (loadingOverlay) { loadingOverlay.style.display = 'none'; }

                        if (formProcesso.id === 'form-processo' && window.location.pathname === FlaskRoutes.processosNovo) {
                            console.log("DEBUG: Processo Novo: Exibindo modal de confirmação para continuar.");
                            const confirmContinue = await new Promise(resolve => {
                                const confirmModalHtml = `
                                    <div class="modal fade" id="continueCadModal" tabindex="-1" aria-labelledby="continueCadModalModalLabel" aria-hidden="true">
                                        <div class="modal-dialog modal-dialog-centered">
                                            <div class="modal-content">
                                                <div class="modal-header">
                                                    <h5 class="modal-title" id="continueCadModalLabel">Processo Cadastrado!</h5>
                                                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                                </div>
                                                <div class="modal-body">
                                                    <p>O processo foi cadastrado com sucesso (ID: ${data.processo_id || 'gerado'}). Deseja cadastrar outro processo?</p>
                                                </div>
                                                <div class="modal-footer">
                                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" id="btnNaoContinuar">Não, obrigado</button>
                                                    <button type="button" class="btn btn-primary" data-bs-dismiss="modal" id="btnSimContinuar">Sim, continuar</button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                `;
                                document.body.insertAdjacentHTML('beforeend', confirmModalHtml);
                                const continueModalEl = document.getElementById('continueCadModal');
                                const continueModal = new bootstrap.Modal(continueModalEl);
                                continueModal.show();
                                console.log("DEBUG: Modal 'continueCadModal' exibido.");

                                continueModalEl.addEventListener('hidden.bs.modal', function (event) {
                                    setTimeout(() => {
                                        if (!this.dataset.resolved) {
                                            console.log("DEBUG: Modal fechado sem escolha, resolvendo promessa como 'Não'.");
                                            this.dataset.resolved = true;
                                            resolve(false);
                                        }
                                        event.target.remove();
                                    }, 50);
                                }, { once: true });

                                document.getElementById('btnSimContinuar').addEventListener('click', () => {
                                    console.log("DEBUG: Usuário clicou em 'Sim, continuar'.");
                                    continueModalEl.dataset.resolved = true;
                                    resolve(true);
                                    continueModal.hide();
                                }, { once: true });

                                document.getElementById('btnNaoContinuar').addEventListener('click', () => {
                                    console.log("DEBUG: Usuário clicou em 'Não, obrigado'.");
                                    continueModalEl.dataset.resolved = true;
                                    resolve(false);
                                    continueModal.hide();
                                }, { once: true });
                            });

                            if (confirmContinue) {
                                console.log("DEBUG: Reiniciando formulário para novo processo (confirmação 'Sim').");
                                formProcesso.reset();
                                currentFiles = [];
                                renderFilePreviews(); // THIS IS THE FUNCTION THAT WAS NOT DEFINED IN SCOPE
                                if (processIdInfo) {
                                    processIdInfo.textContent = `ID será gerada ao salvar`;
                                }
                                updateObservacoesCounter();
                                const dataEntradaField = document.getElementById('data_entrada');
                                if (dataEntradaField) {
                                    const today = new Date();
                                    const year = today.getFullYear();
                                    const month = String(today.getMonth() + 1).padStart(2, '0');
                                    const day = String(today.getDate()).padStart(2, '0');
                                    dataEntradaField.value = `${year}-${month}-${day}`;
                                    validateField.call(dataEntradaField);
                                }
                                if (firstField) { firstField.focus(); }
                            } else {
                                console.log("DEBUG: Redirecionando para a visualização do novo processo usando data.redirect (confirmação 'Não').");
                                window.location.href = data.redirect; 
                            }

                        }
                        else if (data.redirect) {
                            console.log("DEBUG: Redirecionamento via 'data.redirect' (outras rotas de sucesso).");
                            setTimeout(() => {
                                window.location.href = data.redirect;
                            }, 500);
                        } else {
                             console.log("DEBUG: Sucesso sem redirecionamento específico. Recarregando página atual.");
                             setTimeout(() => {
                                window.location.reload();
                             }, 500);
                        }

                    } else {
                        console.log('DEBUG: API Response (Falha de sucesso no servidor):', data);
                        showToast(data.type || 'danger', data.message);
                        if (data.field_error) {
                            const errorField = document.getElementById(data.field_error);
                            if (errorField) {
                                errorField.classList.add('is-invalid');
                                errorField.focus();
                                errorField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            } else if (data.field_error === 'form_fields_missing') {
                                const firstInvalidField = formProcesso.querySelector('.is-invalid');
                                if (firstInvalidField) {
                                    firstInvalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                    firstInvalidField.focus();
                                }
                            }
                        }
                    }
                } else {
                    console.error('ERRO: API Response (Erro HTTP - response.ok é falso):', response.status, response.statusText, data);
                    if (data && data.success === false) {
                        showToast(data.type || 'danger', data.message);
                        if (data.field_error) {
                            const errorField = document.getElementById(data.field_error);
                            if (errorField) {
                                errorField.classList.add('is-invalid');
                                errorField.focus();
                                errorField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            } else if (data.field_error === 'form_fields_missing') {
                                const firstInvalidField = formProcesso.querySelector('.is-invalid');
                                if (firstInvalidField) {
                                    firstInvalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                    firstInvalidField.focus();
                                }
                            }
                        }
                    } else {
                        showToast('danger', `Ocorreu um erro no servidor. Status: ${response.status} ${response.statusText}. Por favor, tente novamente.`);
                    }
                }

            } catch (error) {
                console.error('ERRO CATCH: Erro na requisição Fetch:', error);
                showToast('danger', 'Ocorreu um erro na comunicação com o servidor. Por favor, verifique sua conexão e tente novamente.');
            } finally {
                console.log("DEBUG: Escondendo loading overlay no finally do submit.");
                if (loadingOverlay) { loadingOverlay.style.display = 'none'; }
            }
        } catch (globalError) {
            console.error('ERRO GLOBAL NO EVENT LISTENER SUBMIT:', globalError);
            showToast('danger', 'Ocorreu um erro inesperado no formulário. Por favor, recarregue a página e tente novamente.');
            if (loadingOverlay) { loadingOverlay.style.display = 'none'; }
        }
    });

    // Ao carregar a página de "novo.html", preenche a data de entrada automaticamente
    if (window.location.pathname === FlaskRoutes.processosNovo) {
        const dataEntradaField = document.getElementById('data_entrada');
        if (dataEntradaField) {
            const today = new Date();
            const year = today.getFullYear();
            const month = String(today.getMonth() + 1).padStart(2, '0');
            const day = String(today.getDate()).padStart(2, '0');
            dataEntradaField.value = `${year}-${month}-${day}`;
            validateField.call(dataEntradaField);
        }
    }
}