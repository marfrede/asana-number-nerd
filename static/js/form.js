function validateForm() {
	const checkboxes = Array.from(document.forms["projects_form"].elements).filter(ch => ch.className.includes("project-input"));
	const projects_choosen = checkboxes.filter(ch => ch.checked).length;
	if (projects_choosen <= 0) {
		alert('Please pick at least one project.');
		return false;
	}
	return true;
}