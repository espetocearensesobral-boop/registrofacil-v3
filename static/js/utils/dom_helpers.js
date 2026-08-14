// registrofacil/static/js/utils/dom_helpers.js

/**
 * Exibe uma mensagem Toast personalizada.
 * @param {string} type - Tipo do toast (success, danger, warning, info).
 * @param {string} message - Mensagem a ser exibida.
 */
export function showToast(type, message) {
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        console.error('showToast: Elemento .toast-container não encontrado! Fallback para alert.');
        alert(`Mensagem Toast: ${message}`);
        return;
    }

    let backgroundColor;
    switch(type) {
        case 'success':
            backgroundColor = '#00A86B';
            break;
        case 'danger':
            backgroundColor = '#C5282F';
            break;
        case 'warning':
            backgroundColor = '#FF8C00';
            break;
        case 'info':
            backgroundColor = '#1E88E5';
            break;
        default:
            backgroundColor = '#6C757D';
    }

    const toastHtml = `
        <div class="toast align-items-center text-white border-0" role="alert" aria-live="assertive" style="background-color: ${backgroundColor};">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi bi-${type === 'success' ? 'check-circle-fill' : (type === 'danger' ? 'x-circle-fill' : (type === 'warning' ? 'exclamation-triangle-fill' : 'info-circle-fill'))} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    const toastElement = document.createElement('div');
    toastElement.innerHTML = toastHtml;
    const newToast = toastElement.firstElementChild;
    toastContainer.appendChild(newToast);

    const toast = new bootstrap.Toast(newToast);
    toast.show();

    newToast.addEventListener('hidden.bs.toast', function () {
        newToast.remove();
    });

    console.log(`showToast: Exibindo toast de tipo '${type}' com mensagem: '${message}'`);
}

/**
 * Converte bytes para um formato legível (KB, MB, GB).
 * @param {number} bytes - O número de bytes.
 * @param {number} [decimals=2] - Número de casas decimais.
 * @returns {string} - String formatada (ex: "1.23 MB").
 */
export function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Valida um endereço de e-mail.
 * @param {string} email - O e-mail a ser validado.
 * @returns {boolean} - True se o e-mail for válido, false caso contrário.
 */
export function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/**
 * Valida um número de telefone.
 * @param {string} phone - O telefone a ser validado.
 * @returns {boolean} - True se o telefone for válido, false caso contrário.
 */
export function isValidPhone(phone) {
    // Esta regex permite formatos como (XX) XXXX-XXXX e (XX) XXXXX-XXXX com espaços ou hifens
    const padrao = /^\(?[0-9]{2}\)?[ .-]?[0-9]{4,5}[ .-][0-9]{4}$/;
    return padrao.test(phone);
}


/**
 * Aplica a máscara de telefone (XX) XXXXX-XXXX ou (XX) XXXX-XXXX.
 * @param {string} value - O valor do campo (apenas números).
 * @returns {string} - O valor formatado com a máscara.
 */
export function formatPhoneNumber(value) {
    value = value.replace(/\D/g, ''); // Remove tudo que não é dígito
    if (value.length > 11) {
        value = value.substring(0, 11); // Limita a 11 dígitos
    }

    if (value.length > 10) { // Celular com 9 dígitos: (XX) 9XXXX-XXXX
        return value.replace(/^(\d{2})(\d{5})(\d{4})$/, "($1) $2-$3");
    } else if (value.length > 6) { // Fixo ou celular antigo: (XX) XXXX-XXXX
        return value.replace(/^(\d{2})(\d{4})(\d{4})$/, "($1) $2-$3");
    } else if (value.length > 2) { // Apenas o DDD: (XX) XXXX
        return value.replace(/^(\d{2})(\d+)$/, "($1) $2");
    } else if (value.length > 0) { // Menos que o DDD completo
        return `(${value}`;
    }
    return value;
}


/**
 * Valida uma matrícula.
 * @param {string} matricula - A matrícula a ser validada.
 * @returns {boolean} - True se a matrícula for válida, false caso contrário.
 */
    export function isValidMatricula(matricula) {
    // A regex agora inclui ^ e $ para garantir que a string inteira corresponda ao padrão.
    // Isso evita que strings como "abc!@#" passem na validação se "abc" for válido.
    return /^[A-Za-z0-9\s\-\.\/]{1,50}$/.test(matricula);
}

/**
 * Valida se uma data é futura ou igual à data de hoje.
 * @param {string} dateString - A string da data no formato YYYY-MM-DD.
 * @returns {boolean} - True se a data for futura ou hoje, false caso contrário.
 */
export function isValidFutureOrTodayDate(dateString) {
    const selectedDate = new Date(dateString + 'T00:00:00'); // Garante que a hora seja 00:00:00 GMT
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Zera a hora para comparar apenas a data (no fuso local)

    // Para garantir que a comparação seja precisa e não dependa do fuso horário na criação da data
    // Formatamos today para o mesmo formato YYYY-MM-DD que o dateString
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    const todayFormatted = `${year}-${month}-${day}`;
    
    // Compara as datas já normalizadas para o início do dia
    return selectedDate >= new Date(todayFormatted + 'T00:00:00');
}

/**
 * Alterna a visibilidade de um campo de senha.
 * @param {string} id - O ID do campo de input da senha.
 */
export function togglePassword(id) {
    const input = document.getElementById(id);
    const icon = input.parentElement.querySelector('.toggle-icon i');
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('bi-eye');
        icon.classList.add('bi-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('bi-eye-slash');
        icon.classList.add('bi-eye');
    }
}
// Removido: window.togglePassword = togglePassword; // Expõe a função globalmente para chamadas onclick, pois já é exportada.

// Função MD5 (necessária para Gravatar) - AGORA EXPORTADA!
export function MD5(string) {
    function RotateLeft(lValue, iShiftBits) { return (lValue << iShiftBits) | (lValue >>> (32 - iShiftBits)); }
    function AddUnsigned(lX, lY) { // Esta função AddUnsigned foi simplificada para 2 parâmetros como no original da MD5
        var lX4, lY4, lResult; lX4 = (lX & 0x40000000); lY4 = (lY & 0x40000000); lResult = (lX & 0x3FFFFFFF) + (lY & 0x3FFFFFFF);
        if (lX4 & lY4) { return (lResult ^ 0x80000000 ^ lX4 ^ lY4); }
        if (lX4 | lY4) { if (lResult & 0x40000000) { return (lResult ^ 0xC0000000 ^ lX4 ^ lY4); } else { return (lResult ^ 0x40000000 ^ lX4 ^ lY4); } } else { return (lResult ^ lX4 ^ lY4); }
    }
    function F(x, y, z) { return (x & y) | ((~x) & z); }
    function G(x, y, z) { return (x & z) | (y & (~z)); }
    function H(x, y, z) { return (x ^ y ^ z); }
    function I(x, y, z) { return (y ^ (x | (~z))); }
    function FF(a, b, c, d, x, s, ac) { a = AddUnsigned(a, AddUnsigned(AddUnsigned(F(b, c, d), x), ac)); return AddUnsigned(RotateLeft(a, s), b); }
    function GG(a, b, c, d, x, s, ac) { a = AddUnsigned(a, AddUnsigned(AddUnsigned(G(b, c, d), x), ac)); return AddUnsigned(RotateLeft(a, s), b); }
    function HH(a, b, c, d, x, s, ac) { a = AddUnsigned(a, AddUnsigned(AddUnsigned(H(b, c, d), x), ac)); return AddUnsigned(RotateLeft(a, s), b); }
    function II(a, b, c, d, x, s, ac) { a = AddUnsigned(a, AddUnsigned(AddUnsigned(I(b, c, d), x), ac)); return AddUnsigned(RotateLeft(a, s), b); }
    function ConvertToWordArray(string) {
        var lWordCount; var lMessageLength = string.length; var lNumberOfWords_temp1 = lMessageLength + 8; var lNumberOfWords_temp2 = (lNumberOfWords_temp1 - (lNumberOfWords_temp1 % 64)) / 64; var lNumberOfWords = (lNumberOfWords_temp2 + 1) * 16; var lWordArray = Array(lNumberOfWords - 1); var lBytePosition = 0; var lByteCount = 0;
        for (lWordCount = 0; lWordCount < lNumberOfWords; lWordCount++) { lWordArray[lWordCount] = 0; }
        for (lByteCount = 0; lByteCount < lMessageLength; lByteCount++) { lBytePosition = lByteCount % 4; lWordArray[lByteCount >> 2] |= (string.charCodeAt(lByteCount) & 0xFF) << (lBytePosition * 8); }
        lBytePosition = lByteCount % 4; lWordArray[lByteCount >> 2] |= ((0x80) << (lBytePosition * 8)); lWordArray[lNumberOfWords - 2] = lMessageLength << 3; lWordArray[lNumberOfWords - 1] = lMessageLength >>> 29; return lWordArray;
    }
    function WordToHex(lValue) {
        var WordToHexValue = "", WordToHexValue_temp = "", lByte, lCount;
        for (lCount = 0; lCount <= 3; lCount++) { lByte = (lValue >>> (lCount * 8)) & 0xFF; WordToHexValue_temp = "0" + lByte.toString(16); WordToHexValue = WordToHexValue + WordToHexValue_temp.substr(WordToHexValue_temp.length - 2, 2); }
        return WordToHexValue;
    }
    function Utf8Encode(string) {
        string = string.replace(/\r\n/g, "\n"); var utftext = "";
        for (var n = 0; n < string.length; n++) {
            var c = string.charCodeAt(n);
            if (c < 128) { utftext += String.fromCharCode(c); } else if ((c > 127) && (c < 2048)) { utftext += String.fromCharCode((c >> 6) | 0xC0); utftext += String.fromCharCode((c & 0x3F) | 0x80); } else { utftext += String.fromCharCode((c >> 12) | 0xE0); utftext += String.fromCharCode(((c >> 6) & 0x3F) | 0x80); utftext += String.fromCharCode((c & 0x3F) | 0x80); }
        } return utftext;
    }
    var x = Array(); var k, AA, BB, CC, DD, a, b, c, d; var S11 = 7, S12 = 12, S13 = 17, S14 = 22; var S21 = 5, S22 = 9, S23 = 14, S24 = 20; var S31 = 4, S32 = 11, S33 = 16, S34 = 23; var S41 = 6, S42 = 10, S43 = 15, S44 = 21;
    string = Utf8Encode(string); x = ConvertToWordArray(string); a = 0x67452301; b = 0xEFCDAB89; c = 0x98BADCFE; d = 0x10325476;
    for (k = 0; k < x.length; k += 16) {
        AA = a; BB = b; CC = c; DD = d; a = FF(a, b, c, d, x[k + 0], S11, 0xD76AA478); d = FF(d, a, b, c, x[k + 1], S12, 0xE8C7B756); c = FF(c, d, a, b, x[k + 2], S13, 0x242070DB); b = FF(b, c, d, a, x[k + 3], S14, 0xC1BDCEEE); a = FF(a, b, c, d, x[k + 4], S11, 0xF57C0FAF); d = FF(d, a, b, c, x[k + 5], S12, 0x4787C62A); c = FF(c, d, a, b, x[k + 6], S13, 0xA8304613); b = FF(b, c, d, a, x[k + 7], S14, 0xFD469501); a = FF(a, b, c, d, x[k + 8], S11, 0x698098D8); d = FF(d, a, b, c, x[k + 9], S12, 0x8B44F7AF); c = FF(c, d, a, b, x[k + 10], S13, 0xFFFF5BB1); b = FF(b, c, d, a, x[k + 11], S14, 0x895CD7BE); a = FF(a, b, c, d, x[k + 12], S11, 0x6B901122); d = FF(d, a, b, c, x[k + 13], S12, 0xFD987193); c = FF(c, d, a, b, x[k + 14], S13, 0xA679438E); b = FF(b, c, d, a, x[k + 15], S14, 0x49B40821); a = GG(a, b, c, d, x[k + 1], S21, 0xF61E2562); d = GG(d, a, b, c, x[k + 6], S22, 0xC040B340); c = GG(c, d, a, b, x[k + 11], S23, 0x265E5A51); b = GG(b, c, d, a, x[k + 0], S24, 0xE9B6DBA5); a = GG(a, b, c, d, x[k + 5], S21, 0xD62F105D); d = GG(d, a, b, c, x[k + 10], S22, 0x2441453); c = GG(c, d, a, b, x[k + 15], S23, 0xD8A1E681); b = GG(b, c, d, a, x[k + 4], S24, 0xE7D3FBC8); a = GG(a, b, c, d, x[k + 9], S21, 0x21E1CDE6); d = GG(d, a, b, c, x[k + 14], S22, 0xC33707D6); c = GG(c, d, a, b, x[k + 3], S23, 0xF4D50D87); b = GG(b, c, d, a, x[k + 8], S24, 0x455A14ED); a = GG(a, b, c, d, x[k + 13], S21, 0xA9E3E905); d = GG(d, a, b, c, x[k + 2], S22, 0xFCEFA3F8); c = GG(c, d, a, b, x[k + 7], S23, 0x676F02D9); b = GG(b, c, d, a, x[k + 12], S24, 0x8D2A4C8A); a = HH(a, b, c, d, x[k + 5], S31, 0xFFFA3942); d = HH(d, a, b, c, x[k + 8], S32, 0x8771F681); c = HH(c, d, a, b, x[k + 11], S33, 0x6D9D6122); b = HH(b, c, d, a, x[k + 14], S34, 0xFDE5380C); a = HH(a, b, c, d, x[k + 1], S31, 0xA4BEEA44); d = HH(d, a, b, c, x[k + 4], S32, 0x4BDECFA9); c = HH(c, d, a, b, x[k + 7], S33, 0xF6BB4B60); b = HH(b, c, d, a, x[k + 10], S34, 0xBEBFBC70); a = HH(a, b, c, d, x[k + 13], S31, 0x289B7EC6); d = HH(d, a, b, c, x[k + 0], S32, 0xEAA127FA); c = HH(c, d, a, b, x[k + 3], S33, 0xD4EF3085); b = HH(b, c, d, a, x[k + 6], S34, 0x4881D05); a = HH(a, b, c, d, x[k + 9], S31, 0xD9D4D039); d = HH(d, a, b, c, x[k + 12], S32, 0xE6DB99E5); c = HH(c, d, a, b, x[k + 15], S33, 0x1FA27CF8); b = HH(b, c, d, a, x[k + 2], S34, 0xC4AC5665); a = II(a, b, c, d, x[k + 0], S41, 0xF4292244); d = II(d, a, b, c, x[k + 7], S42, 0x432AFF97); c = II(c, d, a, b, x[k + 14], S43, 0xAB9423A7); b = II(b, c, d, a, x[k + 5], S44, 0xFC93A039); a = II(a, b, c, d, x[k + 12], S41, 0x655B59C3); d = II(d, a, b, c, x[k + 3], S42, 0x8F0CCC92); c = II(c, d, a, b, x[k + 10], S43, 0xFFEFF47D); b = II(b, c, d, a, x[k + 1], S44, 0x85845DD1); a = II(a, b, c, d, x[k + 8], S41, 0x6FA87E4F); d = II(d, a, b, c, x[k + 15], S42, 0xFE2CE6E0); c = II(c, d, a, b, x[k + 6], S43, 0xA3014314); b = II(b, c, d, a, x[k + 13], S44, 0x4E0811A1); a = AddUnsigned(a, AA); b = AddUnsigned(b, BB); c = AddUnsigned(c, CC); d = AddUnsigned(d, DD); } var temp = WordToHex(a) + WordToHex(b) + WordToHex(c) + WordToHex(d); return temp.toLowerCase(); }