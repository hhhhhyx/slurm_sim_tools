cd /opt/slurm_sim_bld
rm -rf slurm_sim_opt
mkdir slurm_sim_opt
cd slurm_sim_opt
/opt/slurm_sim_tools/slurm_simulator/configure --prefix=/opt/slurm_sim \
  --disable-x11 --enable-front-end --disable-dependency-tracking \
  --with-hdf5=no --with-libcurl=/usr \
  CFLAGS='-O3 -Wno-error=unused-variable -Wno-error=implicit-function-declaration' \
  --enable-simulator

make -j$(nproc)
make install