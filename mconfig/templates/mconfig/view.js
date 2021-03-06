//view classes

function Choice(parent, data) {
	//this.name = name;
	var field_node = data.getElementsByTagName('Field')[0];
	var name = field_node.attributes.getNamedItem("name").value;
	//create HTML elements here
	this.edit = document.createElement("input");
	this.update(data)	
};

Choice.prototype.update = function(data){
	var field_node = data.getElementsByTagName('Field')[0];
	var value_node = field_node.getElementsByTagName('value')[0];	
	
	for(var i=this.edit.options.length-1;i>=0;i--){
		this.edit.options.remove(i);
	}
	
	var options = '';
	var choices = field_node.getElementsByTagName('choices')[0];	
	
	choices = choices.getElementsByTagName('choice');
	
	for(var i=0;i<choices.length;i++){
		var option = document.createElement("option");
		option.id = choices[i].attributes.getNamedItem("id").value;
		option.value = choices[i].attributes.getNamedItem("value").value;
		option.text = option.value;
		if(option.value == selected){
			option.selected = true;
		}
		this.edit.options.add(option);						
	}
			
	var selected = "";
	if(value_node.childNodes.length!=0){
		var value = value_node.childNodes[0].nodeValue;
		selected = value;
	}	
	this.edit.value = selected;		
}

Choice.prototype.enable = function(en) {
	this.edit.disabled = !enable;
}

