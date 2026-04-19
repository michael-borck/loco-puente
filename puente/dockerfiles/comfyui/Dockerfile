# ComfyUI — extends mmartial base with packages required by custom nodes.
#
# The mmartial image ships without setuptools (needed by many custom nodes via
# pkg_resources). Installing here means every deploy gets a working base
# without manual "Try Fix" steps in the Manager.
#
# ComfyUI-Manager is installed at runtime via puente's pre_start hook into
# the persistent /basedir/custom_nodes volume, so it stays current with git pull.
FROM mmartial/comfyui-nvidia-docker:ubuntu22_cuda12.4-latest

RUN pip3 install --no-cache-dir setuptools wheel
