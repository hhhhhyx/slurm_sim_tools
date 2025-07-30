cd /opt/slurm_sim_bld/slurm_sim_opt
make LIBS="-lcurl -ljson-c"
make -j$(nproc) && make install