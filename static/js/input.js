document.querySelectorAll('input[name="tipe"]').forEach(radio => {
    radio.addEventListener('change', () => {
    const fotoBlock = document.getElementById('blok-foto');
    if (radio.value === 'return' && radio.checked) {
        fotoBlock.classList.remove('hidden');
    } else if (radio.value === 'void' && radio.checked) {
        fotoBlock.classList.add('hidden');
    }
    });
});