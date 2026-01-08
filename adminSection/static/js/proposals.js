

   // Modal Handling
   function openModal(modalId, data = null) {
     const modal = document.getElementById(modalId);
     modal.classList.add('active');
   }

   function closeModal(modalId) {
     document.getElementById(modalId).classList.remove('active');
   }

   // Proposal Modal Handling
   function openProposalModal(id, data) {
     const modal = document.getElementById('proposal-modal');
     document.getElementById('proposal-student-name').textContent = data.studentName;
     document.getElementById('proposal-title').textContent = data.projectTitle;
     document.getElementById('proposal-description').textContent = data.description;
     document.getElementById('proposal-supervisor').textContent = data.supervisorName;
     document.getElementById('proposal-domains').textContent = data.domains;
     modal.classList.add('active');

     // Store proposal ID for approve/reject actions
     modal.dataset.proposalId = id;
   }

   function approveProposal() {
     const proposalId = document.getElementById('proposal-modal').dataset.proposalId;
     // Backend API call to approve proposal (e.g., PATCH /api/proposals/${proposalId}/approve)
     console.log(`Approve proposal with ID: ${proposalId}`);
     closeModal('proposal-modal');
   }

   function rejectProposal() {
     const proposalId = document.getElementById('proposal-modal').dataset.proposalId;
     // Backend API call to reject proposal (e.g., PATCH /api/proposals/${proposalId}/reject)
     console.log(`Reject proposal with ID: ${proposalId}`);
     closeModal('proposal-modal');
   }