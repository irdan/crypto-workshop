# Objectives

Create reproduceable AZURE VMs for Dan's Workshop SRE inCon 2018.

Should be able to bring up the following resources:

- resource_group
- vm (w/ variable count)
- expose specific ports

Should be able to easily create and tear down environment.

## Install

Running Terraform with Azure providers has two main dependencies: terraform and az.

```bash
$ brew install terraform azure-cli
```

Once installed, cd into this directories and run:

```bash
$ terraform init
```

This will install the azure provider dependencies.

## Login

You will need to follow the instructures here to setup your local environment to use azure cli: https://www.terraform.io/docs/providers/azurerm/authenticating_via_azure_cli.html

Mainly, you will have to do a browser based authentication.

```bash
$ az login
$ az account list
$ az account set --subscription "<'id' from previous command>"
```

## Terroform commands

There are 3 main terraform sub-commands: plan, apply, and destroy.

```bash
$ terraform plan
$ terraform apply
$ terraform destroy
```

- "plan" is essentially just showing what changes it will make based on current state.
- "apply" is actually applying the changes that were planned. This will create the resources per the main.tf file.
- "destroy" this can only delete resources that your terraform is aware off. This state is tracked in terraform.tfstate. Don't manually manage this file. Also note, terraform won't touch any resources that it doesn't have knowledge per the terraform.tfstate file.


And once your terraform apply has finished you can use this command to find the list of VMs to Public IPs:

```bash
$ terraform output vms_and_public_ips
```

## Changes (Variables)

All variables and resources are captured inside the main.tf file. I have tested the workflow with my account and it functions as expected. If you need to, or want to, change any runtime configuration you should checkout the varible at the top of the file. Changing these will have direct impact on the resources that are created and managed by terraform.

You will likely need to only change the "vm_count" default value.

You can also change the contents of the bootstrapping script by editing scripts/bootstrap.sh
