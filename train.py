import argparse, os, pathlib, numpy as np, torch, torch.nn as nn
from torch.nn.utils.rnn import pack_padded_sequence
from utils.preproc import proc
from dataclasses import dataclass
# from icnn.tools.load_data import get_density
# Device configuration
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

def main():
	# Config options
	parser = argparse.ArgumentParser(description='CS2770 Project Train')
	parser.add_argument('data_set', type=str, help='Train on "vqa" or "vqg" questions')
	parser.add_argument('--config', type=pathlib.Path, default='config.ini', help='The config file')
	parser.add_argument('--categoryname', type=str, default='Person', help='classification category')

	args = parser.parse_args()
	root_dir = os.path.dirname(os.path.realpath(__file__))

	encoder, decoder, data_loader, config = proc(args, 'train', root_dir, 'train.py')

	# Create model directory
	if not os.path.exists(config['model_dir']):
		os.makedirs(config['model_dir'])

	# Put models on device
	encoder = encoder.to(device)
	decoder = decoder.to(device)

	# Loss and optimizer
	criterion = nn.CrossEntropyLoss()
	params = list(decoder.parameters()) + list(encoder.linear.parameters()) + list(encoder.bn.parameters())
	optimizer = torch.optim.Adam(params, lr=config['learning_rate'])

	# Train the models
	total_step = len(data_loader)
	category_id_idx = int(config['categories'][args.categoryname])
	for epoch in range(1,config['num_epochs']+1):
		for i, (images, categories, questions, lengths) in enumerate(data_loader):
			# Set mini-batch dataset
			targets = pack_padded_sequence(questions, lengths, batch_first=True, enforce_sorted=False)[0]
			# for image, category_list, question in zip(images, categories, questions):		
			images = images.to(device)
			questions = questions.to(device)
			category  = [category_list[category_id_idx].to(device) for category_list in categories]
			# Forward, backward and optimize
			features = encoder(images, category, torch.Tensor([epoch + 1]),torch.mean(torch.from_numpy(np.arange(1,80)).float())) #encoder(images)
			# outputs = decoder(features, questions, lengths)
			loss = criterion(outputs, targets)
			decoder.zero_grad()
			encoder.zero_grad()
			loss.backward()
			optimizer.step()

			# Print log info
			if i % config['log_step'] == 0:
				print('Epoch [{}/{}], Step [{}/{}], Loss: {:.4f}, Perplexity: {:5.4f}'
					.format(epoch, config['num_epochs'], i, total_step, loss.item(), np.exp(loss.item()))) 
			
		torch.save(decoder.state_dict(), os.path.join(config['model_dir'], f'decoder-{epoch}.pth'))
		torch.save(encoder.state_dict(), os.path.join(config['model_dir'], f'encoder-{epoch}.pth'))


if __name__ == "__main__": main()