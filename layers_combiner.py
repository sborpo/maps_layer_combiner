import sys
import os
import zipfile
import tempfile
import uuid
import shutil
import xml.etree.ElementTree as ET

# Global KMZ properties
g_images_fold = 'images'
g_kml_file = 'doc.kml'

# Just a comment

class KmzFile:
    # Set the namespace
    namespace = 'http://www.opengis.net/kml/2.2'

    # Register the namespace
    ET.register_namespace('', namespace)

    def __init__(self, combined_layer_name):
        template = '<?xml version="1.0" encoding="UTF-8"?><kml xmlns="{}"><Document><name>{}</name></Document></kml>'.format(
            KmzFile.namespace,
            combined_layer_name)
        self.working_directory = tempfile.mkdtemp()
        self.images_tree = os.path.join(self.working_directory, g_images_fold)
        create_dir(self.images_tree)
        self.kml_xml = os.path.join(self.working_directory, g_kml_file)
        self.file_tree = ET.fromstring(template)
        self.document_root = self.file_tree.find('{{{0}}}Document'.format(KmzFile.namespace))
        self.name_tag = '{{{0}}}name'.format(KmzFile.namespace)

    def add_layer(self, layer_root):

        # Copy all the properties
        layer_tree = ET.parse(os.path.join(layer_root, g_kml_file))
        document_elem = layer_tree.find('{{{0}}}Document'.format(KmzFile.namespace))
        if document_elem is None:
            raise Exception('The Document element is not found in the kml file')

        for sub_elem in document_elem:
            if sub_elem.tag != self.name_tag:
                self.document_root.append(sub_elem)

        # Copy all the images
        images_files = dir_content(os.path.join(layer_root, g_images_fold))
        for image in images_files:
            # Copy the images
            shutil.copy(image, self.images_tree)

    def write_kmz_file(self, dest):
        ET.ElementTree(self.document_root).write(self.kml_xml, encoding='UTF-8')
        shutil.make_archive(dest, 'zip', self.working_directory)


def dir_content(dir):
    return [os.path.join(dir, file_name) for file_name in os.listdir(dir)]


def normalize_images(root_path, image_number):
    images_folder = os.path.join(root_path, g_images_fold)
    kml_file = os.path.join(root_path, g_kml_file)
    images = dir_content(images_folder)
    name_map = {}
    for image in images:
        new_image_name = 'combiner_{}.jpg'.format(image_number)
        name_map[os.path.basename(image)] = new_image_name
        os.rename(image, os.path.join(images_folder, new_image_name))
        image_number += 1

    with open(kml_file, 'rb') as kml_file_source:
        content = kml_file_source.read()

    for image_replace in name_map:
        content = content.replace(image_replace, name_map[image_replace])

    with open(kml_file, 'wb') as kml_file_target:
        kml_file_target.write(content)

    return image_number


def create_dir(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


def combine_files(file_paths, target_file):
    image_numbering = 0
    target_file_dir = None
    kmz_file_obj = KmzFile('combined')
    try:
        target_file_dir = tempfile.mkdtemp()
        for kmz_file in file_paths:
            working_directory = None
            try:
                working_directory = tempfile.mkdtemp()
                # Extract the kmz_file content into the working directory
                with zipfile.ZipFile(kmz_file, "r") as zip_ref:
                    zip_ref.extractall(working_directory)
                image_numbering = normalize_images(working_directory, image_numbering)

                # Add the layer to the kmz file
                kmz_file_obj.add_layer(working_directory)

            finally:
                if working_directory is not None:
                    shutil.rmtree(working_directory)

        # Write the kmz file
        kmz_file_obj.write_kmz_file(target_file)

    finally:
        if target_file_dir is not None:
            shutil.rmtree(target_file_dir)


if __name__ == '__main__':

    try:
        source = raw_input('Enter the directory that holds the layers to combine (KMZ files):')
        target_file = raw_input('Enter the file path of the combined file (i.e c:\\combined.kmz')
        files = dir_content(source)
        combine_files(files, target_file)
        print 'Combined layers successfully and saved to: {}'.format(target_file)
    except Exception as e:
        print 'There was an error: {}'.format(e.message)
