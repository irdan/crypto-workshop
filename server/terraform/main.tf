# Below are variables that will let you change
# terraform azure provider plan. Ideally change
# these before running "terraform apply".
variable "vm_count" {
  default   = "4"
}
variable "prefix" {
  default   = "incon-crypto"
}
variable "location" {
  default   = "West US 2"
}
variable "allowed_ports" {
  type    = "list"
  default = ["22", "9501-9502"]
}
variable "admin_user" {
  default = "dantheman"
}
variable "admin_pass" {
  default = "Password1234!"
}
variable "public_ssh_key" {
  default = "~/.ssh/irc.pub"
}
variable "private_ssh_key" {
  default = "~/.ssh/irc"
}
variable "ubuntu_version" {
  default = "18.04-LTS"
}
variable "vm_size" {
  default = "Standard_B1s"
}


# Azure specific resources below
# https://www.terraform.io/docs/providers/azurerm/
##################################################

# - azurerm_resource_group
# - azurerm_virtual_network
# - azurerm_subnet
# - azurerm_public_ip
# - azurerm_network_security_group
# - azurerm_network_interface
# - azurerm_virtual_machine

##################################################
resource "azurerm_resource_group" "main" {
  name     = "${var.prefix}-resource-group"
  location = "${var.location}"
}

resource "azurerm_virtual_network" "main" {
  name                = "${var.prefix}-virtual-network"
  address_space       = ["10.0.0.0/16"]
  location            = "${azurerm_resource_group.main.location}"
  resource_group_name = "${azurerm_resource_group.main.name}"
}

resource "azurerm_subnet" "internal" {
  name                 = "${var.prefix}-subnet"
  resource_group_name  = "${azurerm_resource_group.main.name}"
  virtual_network_name = "${azurerm_virtual_network.main.name}"
  address_prefix       = "10.0.2.0/24"
}

resource "azurerm_public_ip" "main" {
  count                        = "${var.vm_count}"
  name                         = "${var.prefix}-public-ip${count.index}"
  location                     = "${azurerm_resource_group.main.location}"
  resource_group_name          = "${azurerm_resource_group.main.name}"
  public_ip_address_allocation = "Dynamic"
  idle_timeout_in_minutes      = 30
}

resource "azurerm_network_security_group" "main" {
  name                = "${var.prefix}-nsg"
  location            = "${azurerm_resource_group.main.location}"
  resource_group_name = "${azurerm_resource_group.main.name}"

  security_rule {
    name                       = "allow_remote_crypto_in_all"
    description                = "Allow remote protocol in from all locations"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_ranges    = "${var.allowed_ports}"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_interface" "main" {
  count                           = "${var.vm_count}"
  name                            = "${var.prefix}-network-interface${count.index}"
  location                        = "${azurerm_resource_group.main.location}"
  resource_group_name             = "${azurerm_resource_group.main.name}"
  network_security_group_id       = "${azurerm_network_security_group.main.id}"

  ip_configuration {
    name                          = "${var.prefix}-ip-configuration"
    subnet_id                     = "${azurerm_subnet.internal.id}"
    public_ip_address_id          = "${element(azurerm_public_ip.main.*.id, count.index)}"
    private_ip_address_allocation = "dynamic"
  }
}

resource "azurerm_virtual_machine" "main" {
  count                 = "${var.vm_count}"
  name                  = "${var.prefix}-vm${count.index}"
  location              = "${azurerm_resource_group.main.location}"
  resource_group_name   = "${azurerm_resource_group.main.name}"
  network_interface_ids = ["${element(azurerm_network_interface.main.*.id, count.index)}"]
  vm_size               = "${var.vm_size}"

  # Terraform should clean up, but if you manually delete the VM
  # we should try to clean up related resources when applicable.
  delete_os_disk_on_termination = true
  delete_data_disks_on_termination = true

  storage_image_reference {
    publisher = "Canonical"
    offer     = "UbuntuServer"
    sku       = "${var.ubuntu_version}"
    version   = "latest"
  }

  storage_os_disk {
    name              = "${var.prefix}-osdisk${count.index}"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }

  os_profile {
    computer_name  = "${var.prefix}-vm${count.index}"
    admin_username = "${var.admin_user}"
    admin_password = "${var.admin_pass}"
  }

  os_profile_linux_config {
    disable_password_authentication = true

    ssh_keys {
      path     = "/home/${var.admin_user}/.ssh/authorized_keys"
      key_data = "${file(var.public_ssh_key)}"
    }
  }

  tags {
    environment = "${var.prefix}"
  }

  # Provision
  # See: https://www.terraform.io/docs/provisioners/index.html
  provisioner "file" {
    connection {
      type        = "ssh"
      user        = "${var.admin_user}"
      private_key = "${file(var.private_ssh_key)}"
    }
    source      = "scripts/bootstrap.sh"
    destination = "/tmp/bootstrap.sh"
  }
  provisioner "remote-exec" {
    connection {
      type        = "ssh"
      user        = "${var.admin_user}"
      private_key = "${file(var.private_ssh_key)}"
    }
    inline = [
      "chmod +x /tmp/bootstrap.sh",
      "/tmp/bootstrap.sh",
    ]
  }

}

# Aggregate outputs
output "vms_and_public_ips" {
  description = "VM to Public IPs mapping."
  value       = "${zipmap(azurerm_virtual_machine.main.*.name, azurerm_public_ip.main.*.ip_address)}"
}

