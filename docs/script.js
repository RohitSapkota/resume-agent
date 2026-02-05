document.addEventListener('DOMContentLoaded', () => {
    // Keyboard support for horizontal tech stacks
    const scrollContainers = document.querySelectorAll('.tech-stack-container');
    
    scrollContainers.forEach(container => {
        container.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowRight') {
                container.scrollBy({ left: 100, behavior: 'smooth' });
            }
            if (e.key === 'ArrowLeft') {
                container.scrollBy({ left: -100, behavior: 'smooth' });
            }
        });
    });

    // Visual console log for recruiters
    console.log("%c रोहित सापकोटा | Rohit Sapkota ", "color: #45A29E; font-size: 20px; font-weight: bold;");
    console.log("DevOps Engineer and Software Specialist. Welcome to my portfolio.");
});