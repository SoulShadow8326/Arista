document.addEventListener('DOMContentLoaded', function() {
    const footer = document.querySelector('.footer');
    let isScrolling = false;
    let scrollTimer;
    
    footer.style.transition = 'opacity 0.3s ease-in-out';
    footer.style.opacity = '1';
    
    function handleScrollInput() {
        footer.style.opacity = '1';

        clearTimeout(scrollTimer);
        
        scrollTimer = setTimeout(() => {
            footer.style.opacity = '1'; 
        }, 2000);
    }
    const scrollEvents = ['wheel', 'touchmove', 'scroll'];
    scrollEvents.forEach(event => {
        window.addEventListener(event, handleScrollInput, { passive: true });
    });
    footer.style.opacity = '1';
});
