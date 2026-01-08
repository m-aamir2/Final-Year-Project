   // Modal Handling
   function openModal(modalId, data = null) {
    const modal = document.getElementById(modalId);
    modal.classList.add('active');
    if (data && modalId !== 'delete-modal') {
        modal.querySelector('form').reset();
    }
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// Delete Modal Handling
function openDeleteModal(type, id, name) {
    const modal = document.getElementById('delete-modal');
    const message = document.getElementById('delete-message');
    message.textContent = `Are you sure you want to delete ${type} "${name}"?`;
    modal.classList.add('active');

    const confirmBtn = document.getElementById('confirm-delete-btn');
    confirmBtn.onclick = () => {
        // Backend API call to delete (e.g., DELETE /api/${type}/${id})
        console.log(`Delete ${type} with ID: ${id}`);
        closeModal('delete-modal');
    };
}

// Announcement Modal Trigger
document.getElementById('post-announcement-btn').addEventListener('click', () => {
    openModal('announcement-modal');
});
